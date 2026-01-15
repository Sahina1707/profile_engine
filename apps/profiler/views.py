import ollama
from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import FileResponse
from .models import ChatSession, ChatMessage
from apps.core.utils import generate_profile_pdf

class ChatProfilingView(APIView):
    def post(self, request):
        session_id = request.data.get('session_id')
        user_input = request.data.get('text_data') or request.data.get('prompt')
        download_pdf = request.data.get('download_pdf', False)

        # 1. Get or Create Session (Implicit Storage)
        session, _ = ChatSession.objects.get_or_create(session_id=session_id)

        # 2. Retrieve History for AI Context
        history = ChatMessage.objects.filter(session=session)
        messages = [{"role": m.role, "content": m.content} for m in history]
        messages.append({"role": "user", "content": user_input})

        # 3. AI Profiling Logic (Instruction to NOT summarize)
        system_prompt = {
            "role": "system", 
            "content": "You are a Professional Profiler. Identify the domain and build a persona. Do not summarize."
        }
        
        try:
            response = ollama.chat(model='llama3.2', messages=[system_prompt] + messages)
            ai_response = response['message']['content']

            # 4. Save to DB (Persistent Memory)
            ChatMessage.objects.create(session=session, role='user', content=user_input)
            ChatMessage.objects.create(session=session, role='assistant', content=ai_response)
            
            # Implicitly update domain if not set
            if not session.detected_domain:
                session.detected_domain = ai_response.split('\n')[0][:50]
                session.save()

            # 5. Conditional Response Format
            if download_pdf:
                pdf_buffer = generate_profile_pdf(ai_response, session.detected_domain)
                return FileResponse(pdf_buffer, as_attachment=True, filename='Profile_Report.pdf')
            
            return Response({
                "session_id": session_id,
                "domain": session.detected_domain,
                "response": ai_response
            })

        except Exception as e:
            raise Exception(f"Chatbot Engine Error: {str(e)}")