import uuid
from django.contrib.auth.models import AbstractUser, Permission
from django.db import models
from django.conf import settings
from django.utils import timezone


class Role(models.Model):
    """
    Represents a user role with a set of permissions.
    """
    name = models.CharField(max_length=100, unique=True)
    display_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    permissions = models.ManyToManyField(
        Permission,
        blank=True,
        related_name="roles"
    )

    def __str__(self):
        return self.display_name


class User(AbstractUser):
    """
    Custom User model inheriting from AbstractUser.
    This allows for future customization of user fields.
    """
    # Fields for password management features
    password_changed_at = models.DateTimeField(null=True, blank=True)
    force_password_change = models.BooleanField(default=False)
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users"
    )

    # Profile fields
    avatar = models.URLField(max_length=255, blank=True)
    bio = models.TextField(blank=True)
    timezone = models.CharField(max_length=100, default='UTC')
    language = models.CharField(max_length=10, default='en')
    status = models.CharField(max_length=50, blank=True)

    # Notification preferences
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)

    # UI preferences
    theme_preference = models.CharField(max_length=20, default='light')

    # Timestamps
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.username
    
    def get_permissions(self):
        """
        Returns a list of permission strings for the user's role.
        """
        if not self.role or not self.role.is_active:
            return []
        return [f"{p.content_type.app_label}.{p.codename}" for p in self.role.permissions.all()]

class UserSession(models.Model):
    """Model to track user login sessions."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sessions")
    session_key = models.CharField(max_length=100, unique=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Session for {self.user.username} from {self.ip_address}"


class PasswordResetToken(models.Model):
    """Model to store password reset tokens."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="password_reset_tokens")
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    used_by_ip = models.GenericIPAddressField(null=True, blank=True)

    def is_expired(self):
        return timezone.now() > self.expires_at

    def mark_as_used(self, ip_address=None):
        self.is_used = True
        self.used_at = timezone.now()
        self.used_by_ip = ip_address
        self.save(update_fields=['is_used', 'used_at', 'used_by_ip'])
