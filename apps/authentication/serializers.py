
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from apps.users.models import User, Role
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.tokens import RefreshToken

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(write_only=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove username field completely
        if 'username' in self.fields:
            self.fields.pop('username')

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            user = authenticate(
                request=self.context.get('request'),
                username=email, 
                password=password
            )

            if not user:
                raise serializers.ValidationError({"email": "Invalid email or password."})

            refresh = RefreshToken.for_user(user)
            return {
                'email': user.email,
                'user_id': user.id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': user,  
            }

        raise serializers.ValidationError({"email": "Must include email and password."})


    def get_token(self, user):
        token = super().get_token(user)
        token['user_id'] = user.id
        token['email'] = user.email
        token['full_name'] = user.get_full_name()
        token['role'] = user.role.name if user.role else None
        token['permissions'] = user.get_permissions()
        return token

    def get_client_ip(self, request):
        if not request:
            return None
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        return x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    role_name = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = User
        fields = [
            'email', 'first_name', 'last_name', 'password', 'password_confirm', 
            'role_name'
        ]
    
    def validate(self, attrs):
        """Validate registration data"""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password_confirm": "Passwords don't match."})
        
        email = attrs['email']
        # Check if email already exists
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError({"email": "User with this email already exists."})
        
        # Since username is populated with email, check for username uniqueness too.
        # This prevents an IntegrityError at the database level.
        if User.objects.filter(username=email).exists():
            raise serializers.ValidationError({"email": "A user with this username already exists."})
        
        # Validate role if provided, otherwise use default
        role_name = attrs.pop('role_name', None)
        if role_name:
            try:
                role = Role.objects.get(name=role_name, is_active=True)
                attrs['role'] = role
            except Role.DoesNotExist:
                raise serializers.ValidationError({"role_name": f"Role '{role_name}' not found or is not active."})
        else:
            # Assign default role ('agent') if no role is specified.
            try:
                default_role = Role.objects.get(name='agent', is_active=True)
                attrs['role'] = default_role
            except Role.DoesNotExist:
                # Fallback to the first available active role if 'agent' role doesn't exist.
                default_role = Role.objects.filter(is_active=True).first()
                if default_role:
                    attrs['role'] = default_role
                else:
                    raise serializers.ValidationError("Cannot register user: No active roles are configured in the system. Please contact an administrator.")
        
        attrs.pop('password_confirm')
        return attrs
    
    def create(self, validated_data):
        """Create new user"""
        password = validated_data.pop('password')
        # The User model requires a username. We'll use the email for that.
        validated_data['username'] = validated_data['email']
        user = User.objects.create_user(**validated_data, password=password)
        return user


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for password change"""
    
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        """Validate password change data"""
        user = self.context['request'].user
        
        # Check current password
        if not user.check_password(attrs['current_password']):
            raise serializers.ValidationError("Current password is incorrect.")
        
        # Check new passwords match
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError("New passwords don't match.")
        
        return attrs
    
    def save(self):
        """Change user password"""
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.password_changed_at = timezone.now()
        user.force_password_change = False
        user.save(update_fields=['password', 'password_changed_at', 'force_password_change'])
        return user


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for password reset request"""
    
    email = serializers.EmailField()
    # The validation of email existence is handled securely in the view 
    # to prevent leaking information about registered users.


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for password reset confirmation"""
    
    token = serializers.UUIDField()
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        """Validate password reset data"""
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError("Passwords don't match.")
        return attrs


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile data"""
    
    role_name = serializers.CharField(source='role.name', read_only=True)
    role_display_name = serializers.CharField(source='role.display_name', read_only=True)
    permissions = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'avatar', 'bio',
            'timezone', 'language', 'status', 'role_name', 
            'role_display_name', 'permissions',
            'email_notifications', 'sms_notifications', 'theme_preference',
            'last_login', 'date_joined', 'updated_at'
        ]
        read_only_fields = ['id', 'email', 'last_login', 'date_joined', 'updated_at']
    
    def get_permissions(self, obj):
        """Get user permissions"""
        return obj.get_permissions()


class LoginResponseSerializer(serializers.Serializer):
    """Serializer for login response"""
    
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserProfileSerializer()
    
    class Meta:
        fields = ['access', 'refresh', 'user'] 
