from rest_framework.views import exception_handler
from rest_framework.response import Response
from django.conf import settings
import traceback
def global_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        traceback.print_exc()
        error_data = {
            "error": "INTERNAL_SERVER_ERROR",
            "message": "The system encountered an unexpected internal error."
        }
        if settings.DEBUG:
            error_data['details'] = str(exc)

        return Response({
            "errors": error_data
        }, status=500)

    return response