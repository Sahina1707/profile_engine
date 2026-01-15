from urllib import request
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import logout
from django.utils import timezone
from django.conf import settings
from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework.exceptions import ValidationError  
import uuid
import traceback

from apps.users.models import User, PasswordResetToken
from .serializers import (
    CustomTokenObtainPairSerializer,
    UserRegistrationSerializer,
    PasswordChangeSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    UserProfileSerializer, # Used in CustomTokenObtainPairView
    LoginResponseSerializer 
)


# class CustomTokenObtainPairView(TokenObtainPairView):
#     """Custom login view with JWT token generation"""
    
#     serializer_class = CustomTokenObtainPairSerializer
    
#     @extend_schema(
#         summary="User Login",
#         description="Authenticate user and return JWT tokens with user profile data",
#         request=CustomTokenObtainPairSerializer,
#         responses={
#             200: OpenApiResponse(
#                 response=LoginResponseSerializer,
#                 description="Login successful"
#             ),
#             400: OpenApiResponse(description="Invalid credentials"),
#             401: OpenApiResponse(description="Authentication failed"),
#         },
#         tags=["Authentication"]
#     )
#     def post(self, request, *args, **kwargs):
#         serializer = self.get_serializer(data=request.data)
        
#         try:
#             serializer.is_valid(raise_exception=True)
#         except Exception as e:
#             return Response({
#                 'success': False,
#                 'message': 'Login failed',
#                 'errors': serializer.errors
#             }, status=status.HTTP_400_BAD_REQUEST)
        
#         user = serializer.validated_data['user']
#         tokens = serializer.validated_data
        
#         # Create user session record
#         from apps.users.models import UserSession
#         session_expires = timezone.now() + timezone.timedelta(
#             minutes=settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds() / 60
#         )
        
#         UserSession.objects.create(
#             user=user,
#             session_key=request.session.session_key or str(uuid.uuid4()),
#             ip_address=self.get_client_ip(request),
#             user_agent=request.META.get('HTTP_USER_AGENT', ''),
#             expires_at=session_expires
#         )
        
#         # Prepare response
#         user_serializer = UserProfileSerializer(user)
        
#         return Response({
#             'success': True,
#             'message': 'Login successful',
#             'data': {
#                 'access': tokens['access'],
#                 'refresh': tokens['refresh'],
#                 'user': user_serializer.data
#             }
#         }, status=status.HTTP_200_OK)
    
#     def get_client_ip(self, request):
#         """Get client IP address"""
#         x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
#         if x_forwarded_for:
#             ip = x_forwarded_for.split(',')[0]
#         else:
#             ip = request.META.get('REMOTE_ADDR')
#         return ip


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom login view with JWT token generation"""
    
    serializer_class = CustomTokenObtainPairSerializer
    
    @extend_schema(
        summary="User Login",
        description="Authenticate user and return JWT tokens with user profile data",
        request=CustomTokenObtainPairSerializer,
        responses={
            200: OpenApiResponse(
                response=LoginResponseSerializer,
                description="Login successful"
            ),
            400: OpenApiResponse(description="Invalid credentials"),
            401: OpenApiResponse(description="Authentication failed"),
        },
        tags=["Authentication"]
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
            user = serializer.validated_data['user']
            tokens = serializer.validated_data

            # Create user session record
            from apps.users.models import UserSession
            session_expires = timezone.now() + settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME']

            # Get session key safely
            session_key = getattr(request, 'session', None)
            session_key = getattr(session_key, 'session_key', None) or str(uuid.uuid4())

            UserSession.objects.create(
                user=user,
                session_key=session_key,
                ip_address=self.get_client_ip(request) or '0.0.0.0',
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                expires_at=session_expires
            )

            user_serializer = UserProfileSerializer(user)

            return Response({
                'success': True,
                'message': 'Login successful',
                'data': {
                    'access': tokens['access'],
                    'refresh': tokens['refresh'],
                    'user': user_serializer.data
                }
            }, status=status.HTTP_200_OK)
        
        except ValidationError as e:
            return Response({
                'success': False,
                'message': 'Login failed',
                'errors': e.detail 
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            traceback.print_exc()
            return Response({
                "status_code": 500,
                "errors": "Internal server error",
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
class LogoutView(APIView):
    """User logout view"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(
        summary="User Logout",
        description="Logout user and invalidate refresh token",
        responses={
            200: OpenApiResponse(description="Logout successful"),
            401: OpenApiResponse(description="Authentication required"),
        },
        tags=["Authentication"]
    )
    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            # Deactivate user sessions
            from apps.users.models import UserSession
            UserSession.objects.filter(
                user=request.user,
                is_active=True
            ).update(is_active=False)
            
            # Django logout
            logout(request)
            
            return Response({
                'success': True,
                'message': 'Logout successful'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': 'Logout failed',
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class UserRegistrationView(APIView):
    """User registration view"""
    
    permission_classes = [permissions.AllowAny] 
    
    @extend_schema(
        summary="User Registration",
        description="Register a new user account",
        request=UserRegistrationSerializer,
        responses={
            201: OpenApiResponse(
                response=UserProfileSerializer,
                description="User created successfully"
            ),
            400: OpenApiResponse(description="Validation errors"),
        },
        tags=["Authentication"]
    )
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.save()
            user_data = UserProfileSerializer(user).data
            
            return Response({
                'success': True,
                'message': 'User registered successfully',
                'data': user_data
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'message': 'Registration failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class PasswordChangeView(APIView):
    """Password change view for authenticated users"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(
        summary="Change Password",
        description="Change user password (requires current password)",
        request=PasswordChangeSerializer,
        responses={
            200: OpenApiResponse(description="Password changed successfully"),
            400: OpenApiResponse(description="Validation errors"),
            401: OpenApiResponse(description="Authentication required"),
        },
        tags=["Authentication"]
    )
    def post(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save()
            
            return Response({
                'success': True,
                'message': 'Password changed successfully'
            }, status=status.HTTP_200_OK)
        
        return Response({
            'success': False,
            'message': 'Password change failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetRequestView(APIView):
    """Password reset request view"""
    
    permission_classes = [permissions.AllowAny]
    
    @extend_schema(
        summary="Request Password Reset",
        description="Request password reset token via email",
        request=PasswordResetRequestSerializer,
        responses={
            200: OpenApiResponse(description="Reset email sent (if email exists)"),
            400: OpenApiResponse(description="Validation errors"),
        },
        tags=["Authentication"]
    )
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        
        if serializer.is_valid():
            email = serializer.validated_data['email']
            
            try:
                user = User.objects.get(email=email, is_active=True)
                
                # Create password reset token
                reset_token = PasswordResetToken.objects.create(
                    user=user,
                    expires_at=timezone.now() + timezone.timedelta(hours=24)
                )
                
                # TODO: Send email with reset token
                # This would integrate with email service
                
                return Response({
                    'success': True,
                    'message': 'If the email exists, a reset link has been sent'
                }, status=status.HTTP_200_OK)
                
            except User.DoesNotExist:
                # Don't reveal if email exists for security
                return Response({
                    'success': True,
                    'message': 'If the email exists, a reset link has been sent'
                }, status=status.HTTP_200_OK)
        
        return Response({
            'success': False,
            'message': 'Invalid email address',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetConfirmView(APIView):
    """Password reset confirmation view"""
    
    permission_classes = [permissions.AllowAny]
    
    @extend_schema(
        summary="Confirm Password Reset",
        description="Reset password using token",
        request=PasswordResetConfirmSerializer,
        responses={
            200: OpenApiResponse(description="Password reset successful"),
            400: OpenApiResponse(description="Invalid token or validation errors"),
        },
        tags=["Authentication"]
    )
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        
        if serializer.is_valid():
            token_uuid = serializer.validated_data['token']
            new_password = serializer.validated_data['new_password']
            
            try:
                reset_token = PasswordResetToken.objects.get(
                    token=token_uuid,
                    is_used=False
                )
                
                if reset_token.is_expired():
                    return Response({
                        'success': False,
                        'message': 'Reset token has expired'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Reset password
                user = reset_token.user
                user.set_password(new_password)
                user.password_changed_at = timezone.now()
                user.force_password_change = False
                user.save(update_fields=['password', 'password_changed_at', 'force_password_change'])
                
                # Mark token as used
                reset_token.mark_as_used(
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
                return Response({
                    'success': True,
                    'message': 'Password reset successful'
                }, status=status.HTTP_200_OK)
                
            except PasswordResetToken.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'Invalid or expired reset token'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'success': False,
            'message': 'Password reset failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(RetrieveUpdateAPIView):
    """View to retrieve and update user profile."""
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def check_auth_status(request):
    """Check if user is authenticated and return basic info"""
    
    return Response({
        'success': True,
        'authenticated': True,
        'user': {
            'id': request.user.id,
            'username': request.user.username,
            'email': request.user.email,
            'full_name': request.user.get_full_name(),
        }
    }, status=status.HTTP_200_OK) 
