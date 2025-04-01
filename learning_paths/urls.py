"""
URLs for learning_paths.
"""

from django.urls import include, path

urlpatterns = [
    path("api/learning_paths/", include("learning_paths.api.urls")),
]
