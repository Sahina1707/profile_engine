from django.urls import path
from .views import ChatProfilingView
urlpatterns = [
    path('explain/', ChatProfilingView.as_view(), name='explain-profile'),
]