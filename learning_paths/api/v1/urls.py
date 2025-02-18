""" API v1 URLs. """

from django.urls import path
from rest_framework import routers

from learning_paths.api.v1.views import (
    LearningPathAsProgramViewSet,
    LearningPathUserGradeView,
    LearningPathUserProgressView,
    LearningPathViewSet,
)

router = routers.SimpleRouter()
router.register(
    r"programs", LearningPathAsProgramViewSet, basename="learning-path-as-program"
)
router.register(r"learning-paths", LearningPathViewSet, basename="learning-path")

urlpatterns = router.urls + [
    path(
        "learning-paths/<uuid:learning_path_uuid>/progress/",
        LearningPathUserProgressView.as_view(),
        name="learning-path-progress",
    ),
    path(
        "learning-paths/<uuid:learning_path_uuid>/grade/",
        LearningPathUserGradeView.as_view(),
        name="learning-path-grade",
    ),
]
