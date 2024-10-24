""" API v1 URLs. """

from django.urls import path
from rest_framework import routers

from learning_paths.api.v1.views import (
    LearningPathAsProgramViewSet,
    learning_path_progress_view,
)

router = routers.SimpleRouter()
router.register(
    r"programs", LearningPathAsProgramViewSet, basename="learning-path-as-program"
)

urlpatterns = router.urls + [
    path(
        "learning-paths/<uuid:learning_path_uuid>/progress/",
        learning_path_progress_view,
        name="learning-path-progress",
    ),
]
