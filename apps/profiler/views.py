import uuid
import json
import hashlib
import docx
import ollama
import fitz
from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import FileResponse
from django.conf import settings
from django.db.models import Q
from .models import (
    ChatSession,
    RawUserInput,
    NormalizedContext,
    ProfilingInference,
    GeneratedOutput,
)
from apps.core.utils import generate_profile_pdf
from django.db import transaction

def safe_list(value):
    return value if isinstance(value, list) else []

def build_narrative_from_profile(profile_json: dict):
    # This must match the NEW JSON keys in the prompt above
    subject = profile_json.get("profile_subject", "The subject")
    domain = profile_json.get("profile_domain", "an unspecified domain")
    
    # Use the same keys the AI is actually sending
    strengths = ", ".join(safe_list(profile_json.get("strengths")))
    limitations = ", ".join(safe_list(profile_json.get("limitations")))
    risks = ", ".join(safe_list(profile_json.get("risks_or_gaps")))

    confidence_pct = int(profile_json.get("confidence_score", 0) * 100)

    return (
        f"{subject} operates in {domain}. "
        f"Key assets: {strengths or 'None'}. "
        f"Constraints: {limitations or 'None'}. "
        f"Risks: {risks or 'None'}. "
        f"Profile Confidence: {confidence_pct}%."
    )
def extract_json_and_narrative(ai_output: str):
    """
    Universal Parser: Isolates JSON for the database and Narrative for the user.
    If JSON is missing, it treats the whole output as the Narrative.
    """
    try:
        # Locate the JSON boundaries
        start_index = ai_output.find("{")
        end_index = ai_output.rfind("}")

        if start_index == -1 or end_index == -1:
            # No JSON found, return empty dict and full text
            return {}, ai_output.strip()

        json_part = ai_output[start_index:end_index + 1]
        narrative_part = ai_output[end_index + 1:].strip()

        # Clean up common AI markers
        narrative_part = narrative_part.replace("[Narrative]", "").replace("Professional Diagnostic:", "").strip()

        return json.loads(json_part), narrative_part
    except Exception:
        # If parsing fails, fallback to raw text
        return {}, ai_output.strip()
class ProfileEngineAPI(APIView):
    def post(self, request):
        # 1. INITIALIZE DATA (Matches Postman keys)
        session_id = request.data.get("session_id") or str(uuid.uuid4())
        user_prompt = request.data.get("prompt") # Key matches Postman
        text_data = request.data.get("text_data", "")
        
        # Change this to "file" to match your Postman screenshot
        uploaded_file = request.FILES.get("file") 
        
        if not user_prompt:
            return Response({"error": "Prompt is required"}, status=400)

        session, _ = ChatSession.objects.get_or_create(session_id=session_id)

        # 2. EXTRACT TEXT
        extracted_text = text_data
        if uploaded_file:
            uploaded_file.seek(0)
            ext = uploaded_file.name.lower()
            try:
                # Handle .docx as shown in your Postman screenshot
                if ext.endswith(".docx"):
                    doc = docx.Document(uploaded_file)
                    extracted_text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
                elif ext.endswith(".pdf"):
                    pdf_data = uploaded_file.read()
                    pdf_document = fitz.open(stream=pdf_data, filetype="pdf")
                    extracted_text = "\n".join([page.get_text() for page in pdf_document])
                    pdf_document.close()
            except Exception as e:
                return Response({"error": f"Extraction failed: {str(e)}"}, status=500)

        # 3. VALIDATION (The line triggering your current error)
        if not extracted_text.strip():
            return Response({"error": "No context data found in input."}, status=400)

        # 4. PREPARE AI REQUEST
        system_prompt = """
You are the Universal Profile Engine. 
Your task is to deconstruct ANY input into a standardized structural profile.

MANDATORY OUTPUT FORMAT:
1. Your response MUST start with a JSON object.
2. After the JSON, provide a "Professional Diagnostic" narrative.

JSON SCHEMA:
{
  "profile_subject": "Name of the entity/person",
  "profile_domain": "Category (e.g., Hospitality, AI Tech, HR)",
  "strengths": ["Asset 1", "Asset 2"],
  "limitations": ["Bottleneck 1", "Constraint 2"],
  "risks_or_gaps": ["Market/Safety Risk", "Missing Data"],
  "confidence_score": 0.0
}

RULES:
- NO PLACEHOLDERS: Use only names/facts found in the context.
- INFERENCE: If '18 staff' for '60 seats', infer 'High Labor Overhead'.
- FALLBACK: If a field is unknown, use 'Not provided in context'.
"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"CONTEXT DATA:\n\"\"\"\n{extracted_text}\n\"\"\"\n\nINTENT: {user_prompt}"}
        ]

        # 5. EXECUTE AI AND SAVE
        try:
            response = ollama.chat(
                model="llama3.2", 
                messages=messages, 
                format="json",
                options={"temperature": 0}
            )
            ai_raw_output = response["message"]["content"]
            profile_json, narrative = extract_json_and_narrative(ai_raw_output)
            
            # This is where the error was triggered; we MUST handle the exception first
        except Exception as e:
            return Response({"error": f"Process failed: {str(e)}"}, status=500)

        # 6. NARRATIVE LOGIC (Now placed correctly outside the try-except block)
        if not narrative or narrative.strip().startswith("{"):
            final_content = build_narrative_from_profile(profile_json)
        else:
            final_content = narrative
            
        # 7. DATABASE PERSISTENCE
        with transaction.atomic():
            ProfilingInference.objects.create(
                session=session,
                profile_subject=profile_json.get("profile_subject", "Unknown"),
                inferred_domain=profile_json.get("profile_domain", "Unknown"),
                strengths=profile_json.get("strengths", []),
                limitations=profile_json.get("limitations", []),
                risks_or_gaps=profile_json.get("risks_or_gaps", []),
                confidence_score=profile_json.get("confidence_score", 0.0)
            )
            GeneratedOutput.objects.create(
                session=session,
                output_type="chat",
                content=final_content
            )
        output_format = request.data.get("format", "text").lower()

        if output_format == "pdf":
            try:
                # Use the utility to create the PDF byte stream
                pdf_file = generate_profile_pdf(
                    final_content, 
                    profile_json.get("profile_domain", "Universal Report")
                )
                
                # Stream the file back to the user with a dynamic name
                filename = f"{profile_json.get('profile_subject', 'Profile')}_Report.pdf".replace(" ", "_")
                
                return FileResponse(
                    pdf_file, 
                    as_attachment=True, 
                    filename=filename,
                    content_type='application/pdf'
                )
            except Exception as e:
                return Response({"error": f"PDF Generation failed: {str(e)}"}, status=500)

        # Default: Return the standard JSON response for the UI
        return Response({
            "session_id": session_id,
            "response": final_content,
            "structured_data": profile_json
        })

