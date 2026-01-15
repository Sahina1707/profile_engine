from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.http import JsonResponse
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from django.urls import path

api_patterns = [
    path('profiler/', include('apps.profiler.urls')),
    
    path('auth/', include('apps.authentication.urls')),
    path('users/', include('apps.users.urls')),
]

urlpatterns = [
    path(f'{settings.ADMIN_URL if hasattr(settings, "ADMIN_URL") else "admin/"}', admin.site.urls),
    path('api/', include(api_patterns)),
    path('health/', lambda request: JsonResponse({'status': 'healthy'})),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema')),
]