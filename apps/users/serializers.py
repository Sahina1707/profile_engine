from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    """Serializer for the custom User model."""
    class Meta:
        model = User
        # Expose a safe subset of fields.
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id']

