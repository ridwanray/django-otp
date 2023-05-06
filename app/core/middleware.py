from django.conf import settings
from django.http import JsonResponse, HttpResponse

from sentry_sdk import capture_exception


class CaptureExceptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        if exception:
            capture_exception(exception)
            return JsonResponse(
                {"success": False, "detail": str(exception)}, status=500
            )

