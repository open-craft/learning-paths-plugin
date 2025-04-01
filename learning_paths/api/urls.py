"""API URLs."""

from django.urls import include, path

urlpatterns = [
    path("v1/", include("learning_paths.api.v1.urls")),
]
