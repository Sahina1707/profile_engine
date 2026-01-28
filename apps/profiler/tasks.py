from celery import shared_task
from .engine import run_profile_engine
from .models import ChatSession

@shared_task
def process_profile_background(profile_data, session_id):
    session = ChatSession.objects.get(session_id=session_id)
    return run_profile_engine(profile_data, session)