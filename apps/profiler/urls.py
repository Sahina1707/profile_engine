from django.urls import path
from .views import ProfileEngineAPI,DownloadProfileOutputAPI
urlpatterns = [
    path("profile/", ProfileEngineAPI.as_view(), name="profile-engine"),
    path('download/<int:output_id>/', DownloadProfileOutputAPI.as_view(), name='download-profile'),

]
