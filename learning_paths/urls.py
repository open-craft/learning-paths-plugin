"""
URLs for learning_paths.
"""

from django.urls import include, path

urlpatterns = [
    path("api/", include("learning_paths.api.urls")),
]
