"""API v1 URLs."""

from django.urls import path
from rest_framework import routers

from learning_paths.api.v1.views import (
    BulkEnrollView,
    LearningPathAsProgramViewSet,
    LearningPathEnrollmentView,
    LearningPathUserGradeView,
    LearningPathUserProgressView,
    ListEnrollmentsView,
)

router = routers.SimpleRouter()
router.register(
    r"programs", LearningPathAsProgramViewSet, basename="learning-path-as-program"
)

urlpatterns = router.urls + [
    path(
        "<uuid:learning_path_uuid>/progress/",
        LearningPathUserProgressView.as_view(),
        name="learning-path-progress",
    ),
    path(
        "<uuid:learning_path_uuid>/grade/",
        LearningPathUserGradeView.as_view(),
        name="learning-path-grade",
    ),
    path(
        "<uuid:learning_path_id>/enrollments/",
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
