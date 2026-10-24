from django.urls import path

from api.views import health, ping

urlpatterns = [
    path("api/health/", health, name="health"),
    path("api/ping/", ping, name="ping"),
]
