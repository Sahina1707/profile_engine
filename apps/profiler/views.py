from rest_framework.views import APIView
from rest_framework.response import Response
import uuid
from .models import ChatSession
from .engine import run_profile_engine

class ProfileEngineAPI(APIView):
    def post(self, request):
        session_id = request.data.get("session_id")
        session, _ = ChatSession.objects.get_or_create(
            session_id=session_id or str(uuid.uuid4())
        )

        profiles_input = request.data.get("profiles") or [{
            "text_data": request.data.get("text_data"),
            "file": request.FILES.get("file"),
        }]

        # WE REMOVED .delay() HERE - It now runs directly
        results = [
            run_profile_engine(profile, session)
            for profile in profiles_input
        ]

        return Response({
            "session_id": str(session.session_id),
            "profiles": results,
        })