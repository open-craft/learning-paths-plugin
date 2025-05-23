"""API v1 URLs."""

from django.urls import path, re_path
from rest_framework import routers

from learning_paths.api.v1.views import (
    BulkEnrollView,
    LearningPathAsProgramViewSet,
    LearningPathCourseEnrollmentView,
    LearningPathEnrollmentView,
    LearningPathUserGradeView,
    LearningPathUserProgressView,
    LearningPathViewSet,
    ListEnrollmentsView,
)
from learning_paths.keys import COURSE_KEY_URL_PATTERN, LEARNING_PATH_URL_PATTERN

router = routers.SimpleRouter()
router.register(r"programs", LearningPathAsProgramViewSet, basename="learning-path-as-program")
router.register(r"learning-paths", LearningPathViewSet, basename="learning-path")

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
        rf"{LEARNING_PATH_URL_PATTERN}/enrollments/$",
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
    re_path(
        rf"{LEARNING_PATH_URL_PATTERN}/enrollments/{COURSE_KEY_URL_PATTERN}/",
        LearningPathCourseEnrollmentView.as_view(),
        name="learning-path-course-enroll",
    ),
]
