from django.urls import path
from .views import ProfileEngineAPI

urlpatterns = [
    path("profile/", ProfileEngineAPI.as_view(), name="profile-engine"),
]
