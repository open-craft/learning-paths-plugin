"""API v1 URLs."""

from django.urls import path, re_path
from rest_framework import routers

from learning_paths.api.v1.views import (
    BulkEnrollView,
    LearningPathAsProgramViewSet,
    LearningPathEnrollmentView,
    LearningPathUserGradeView,
    LearningPathUserProgressView,
    ListEnrollmentsView,
)
from learning_paths.keys import LEARNING_PATH_URL_PATTERN

router = routers.SimpleRouter()
router.register(
    r"programs", LearningPathAsProgramViewSet, basename="learning-path-as-program"
)

urlpatterns = router.urls + [
    re_path(
        rf"{LEARNING_PATH_URL_PATTERN}/progress/",
        LearningPathUserProgressView.as_view(),
        name="learning-path-progress",
    ),
    re_path(
        rf"{LEARNING_PATH_URL_PATTERN}/grade/",
        LearningPathUserGradeView.as_view(),
        name="learning-path-grade",
    ),
    re_path(
        rf"{LEARNING_PATH_URL_PATTERN}/enrollments/",
        LearningPathEnrollmentView.as_view(),
        name="learning-path-enrollments",
    ),
    path(
        "enrollments/",
        ListEnrollmentsView.as_view(),
        name="list-enrollments",
    ),
    path(
        "enrollments/bulk-enroll/",
        BulkEnrollView.as_view(),
        name="bulk-enroll",
    ),
]
