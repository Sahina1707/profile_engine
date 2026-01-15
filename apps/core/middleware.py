import time

class ImplicitSignalMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.start_time = time.time()
        response = self.get_response(request)
        
        # Log system-level signals (like processing duration)
        duration = time.time() - request.start_time
        print(f"System Signal: Request processed in {duration:.2f}s")
        
        return response