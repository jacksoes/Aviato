from django.db import connections
from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def ping(request):
    """Return a lightweight response for frontend connectivity checks."""
    return JsonResponse({"message": "pong"})


@require_GET
def health(request):
    """Report API status and whether MongoDB can be reached."""
    try:
        database = connections["default"]
        database.ensure_connection()
        database.connection.admin.command("ping")
    except Exception:
        return JsonResponse(
            {"status": "error", "database": "disconnected"}, status=503
        )
    return JsonResponse({"status": "ok", "database": "connected"})
