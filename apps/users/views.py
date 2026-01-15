from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import User
from .serializers import UserSerializer


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    Provides a view for authenticated users to retrieve and update their profile.
    """
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)   