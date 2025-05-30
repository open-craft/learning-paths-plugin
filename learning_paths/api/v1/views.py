"""
Views for LearningPath.
"""

import logging
from datetime import datetime, timezone

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.core.validators import validate_email
from django.shortcuts import get_object_or_404
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey
from rest_framework import generics, status, viewsets
from rest_framework.exceptions import NotFound, ParseError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from learning_paths.api.v1.serializers import (
    LearningPathAsProgramSerializer,
    LearningPathDetailSerializer,
    LearningPathEnrollmentSerializer,
    LearningPathGradeSerializer,
    LearningPathListSerializer,
    LearningPathProgressSerializer,
)
from learning_paths.compat import enroll_user_in_course
from learning_paths.keys import LearningPathKey
from learning_paths.models import (
    LearningPath,
    LearningPathEnrollment,
    LearningPathEnrollmentAllowed,
)

from .filters import AdminOrSelfFilterBackend
from .permissions import IsAdminOrSelf
from .utils import get_aggregate_progress

logger = logging.getLogger(__name__)

User = get_user_model()


class LearningPathAsProgramViewSet(viewsets.ReadOnlyModelViewSet):
    """
    This viewset exposes LearningPaths as Programs to be ingested
    by the course-discovery's refresh_course_metadata command.
    URL is: GET <LMS_URL>/api/v1/programs
    The command makes use of the ProgramsApiDataLoader.
    https://github.com/openedx/course-discovery/blob/d6a57fd69479b3d5f5afb682d2668b58503a6af6/course_discovery/apps/course_metadata/data_loaders/api.py#L843
    """

    permission_classes = (IsAuthenticated,)
    serializer_class = LearningPathAsProgramSerializer
    pagination_class = PageNumberPagination

    def get_queryset(self):
        """Get the learning paths visible to the current user."""
        return LearningPath.objects.get_paths_visible_to_user(self.request.user)


class LearningPathUserProgressView(APIView):
    """
    API view to return the aggregate progress of a user in a learning path.
    """

    permission_classes = (IsAuthenticated,)

    def get(self, request, learning_path_key_str: str):
        """
        Fetch the learning path progress
        """
        learning_path = get_object_or_404(
            LearningPath.objects.get_paths_visible_to_user(self.request.user),
            key=learning_path_key_str,
        )

        progress = get_aggregate_progress(request.user, learning_path)
        required_completion = None
        try:
            grading_criteria = learning_path.grading_criteria
            required_completion = grading_criteria.required_completion
        except ObjectDoesNotExist:
            pass

        data = {
            "learning_path_key": learning_path_key_str,
            "progress": progress,
            "required_completion": required_completion,
        }

        serializer = LearningPathProgressSerializer(data=data)
        if serializer.is_valid():
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LearningPathUserGradeView(APIView):
    """
    API view to return the aggregate grade of a user in a learning path.
    """

    permission_classes = (IsAuthenticated,)

    def get(self, request, learning_path_key_str: str):
        """
        Fetch learning path grade
        """

        learning_path = get_object_or_404(
            LearningPath.objects.get_paths_visible_to_user(self.request.user),
            key=learning_path_key_str,
        )

        try:
            grading_criteria = learning_path.grading_criteria
        except ObjectDoesNotExist:
            return Response(
                {"detail": "Grading criteria not found for this learning path."},
                status=status.HTTP_404_NOT_FOUND,
            )

        grade = grading_criteria.calculate_grade(request.user)

        data = {
            "learning_path_key": learning_path_key_str,
            "grade": grade,
            "required_grade": grading_criteria.required_grade,
        }

        serializer = LearningPathGradeSerializer(data=data)
        if serializer.is_valid():
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LearningPathViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for listing all learning paths and retrieving a specific learning path's details,
    including steps and associated skills.
    """

    permission_classes = (IsAuthenticated,)
    pagination_class = PageNumberPagination
    lookup_field = "key"

    def get_queryset(self):
        """
        Get all learning paths and prefetch the related data.
        """
        user = self.request.user
        queryset = LearningPath.objects.get_paths_visible_to_user(user).prefetch_related(
            "steps",
            "grading_criteria",
        )
        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return LearningPathListSerializer
        return LearningPathDetailSerializer

    def get_object(self):
        """Gracefully handle an invalid learning path key format."""
        try:
            return super().get_object()
        except InvalidKeyError as exc:
            raise NotFound("Invalid learning path key format.") from exc


class LearningPathEnrollmentView(APIView):
    """
    API View to handle changes to LearningPathEnrollment model
    """

    permission_classes = [IsAuthenticated, IsAdminOrSelf]

    def _get_learning_path(self, learning_path_key_str: str) -> LearningPath:
        """
        Get the learning path and verify user has access to it.

        :raises: Http404 if the learning path is not found or user does not have access.
        """
        return get_object_or_404(
            LearningPath.objects.get_paths_visible_to_user(self.request.user),
            key=learning_path_key_str,
        )

    def get(self, request, learning_path_key_str: str):
        """Get the learning path of users.

        Staff/Admin can get all the active enrollments of the learning path.
        Learners can get their enrollments only.

        Query params:
            username (optional): When provided it returns the enrollment for
                the specified user.
        """
        learning_path = self._get_learning_path(learning_path_key_str)

        enrollments = LearningPathEnrollment.objects.filter(learning_path=learning_path, is_active=True)

        if request.user.is_staff:
            if username := request.query_params.get("username"):
                enrollments = enrollments.filter(user__username=username)
        else:
            enrollments = enrollments.filter(user=request.user)

        serializer = LearningPathEnrollmentSerializer(enrollments.all(), many=True)
        return Response(serializer.data)

    def post(self, request, learning_path_key_str: str):
        """Enroll learners in Learning Paths.

        Staff/Admin can enroll anyone with the username query param.
        Learners can enroll only themselves, and only if the learning path is not invite-only.

        Example payload::

            {
                "username": "user_1"
            }

        """
        learning_path = self._get_learning_path(learning_path_key_str)
        username = request.data.get("username")
        user = get_object_or_404(User, username=username) if username else request.user

        enrollment, created = LearningPathEnrollment.objects.get_or_create(learning_path=learning_path, user=user)
        if created:
            return Response(
                LearningPathEnrollmentSerializer(enrollment).data,
                status=status.HTTP_201_CREATED,
            )
        if enrollment.is_active:
            return Response({"detail": "Enrollment exists."}, status=status.HTTP_409_CONFLICT)

        enrollment.is_active = True
        enrollment.enrolled_at = datetime.now(timezone.utc)
        enrollment.save()
        return Response(LearningPathEnrollmentSerializer(enrollment).data)

    def delete(self, request, learning_path_key_str: str):
        """
        Unenroll a learner from a learning path.

        Staff/admin can unenroll anyone with the username query param.
        Learners can self-unenroll if settings.LEARNING_PATHS_ALLOW_SELF_UNENROLLMENT is True.

        Example payload::

            {
                "username": "user_1"
            }

        """
        learning_path = self._get_learning_path(learning_path_key_str)
        username = request.data.get("username")
        user = get_object_or_404(User, username=username) if username else request.user

        enrollment = get_object_or_404(
            LearningPathEnrollment,
            learning_path=learning_path,
            is_active=True,
            user=user,
        )

        if not request.user.is_staff and not settings.LEARNING_PATHS_ALLOW_SELF_UNENROLLMENT:
            raise PermissionDenied

        enrollment.is_active = False
        enrollment.save()
        return Response(
            LearningPathEnrollmentSerializer(enrollment).data,
            status=status.HTTP_204_NO_CONTENT,
        )


class ListEnrollmentsView(generics.ListAPIView):
    """
    List Learning Path Enrollments.

    For staff, this returns enrollments from all learning paths for all users.
    For non-staff, this returns all enrollments for the current user.
    """

    permission_classes = [IsAuthenticated]
    queryset = LearningPathEnrollment.objects.all()
    serializer_class = LearningPathEnrollmentSerializer
    filter_backends = [AdminOrSelfFilterBackend]


class BulkEnrollView(APIView):
    """
    Bulk enrollment API for LearningPathEnrollment.

    """

    permission_classes = [IsAdminUser]

    def post(self, request, *args, **kwargs):
        """
        Bulk Enroll learners in Learning Paths.

        The "bulk enroll" API provides a way for the staff to enroll multiple learners
        in multiple learning paths at once.

        Example payload::

            {
                "learning_paths": "learning_path_1,learning_path_2",
                "emails": "user_1@example.com,user_2@example.com"
            }

        `learning_paths` (str): A comma separated list of learning path IDs.
        `emails` (str): A comma separated list of email addresses.

        * For existing users, it creates a new LearningPathEnrollment record, automatically
          enrolling them in the learning path. It also creates a LearningPathAllowed record
          to store the meta-data for audit later.
        * For non-existing users, it creates a new LearningPathEnrollmentAllowed record
          with just the email address, allowing them to get enrolled when they register.

        """
        data = request.data
        learning_paths_keys = data.get("learning_paths", "").split(",")
        emails = data.get("emails", "").split(",")

        valid_learning_paths_keys = []
        for key in learning_paths_keys:
            try:
                LearningPathKey.from_string(key)
                valid_learning_paths_keys.append(key)
            except InvalidKeyError:
                logger.warning("BulkEnrollView: Invalid learning path key: %s", key)

        learning_paths = LearningPath.objects.filter(key__in=valid_learning_paths_keys)

        existing_users = User.objects.filter(email__in=emails)
        non_existing_emails = set(emails) - set(u.email for u in existing_users)

        enrollments_created = []
        enrollment_allowed_created = []

        for learning_path in learning_paths:

            # Create LearningPathEnrollment for existing users
            for user in existing_users:
                enrollment = LearningPathEnrollment.objects.filter(user=user, learning_path=learning_path).first()
                enrolled_now = False
                if not enrollment:
                    enrollment = LearningPathEnrollment(
                        user=user,
                        learning_path=learning_path,
                    )
                    enrolled_now = True
                if not enrollment.is_active:
                    enrollment.is_active = True
                    enrollment.enrolled_at = datetime.now(timezone.utc)
                    enrolled_now = True
                enrollment.save()
                if enrolled_now:
                    enrollments_created.append(enrollment)

            # Create LearningPathEnrollmentAllowed for non-existing users
            for email in non_existing_emails:
                try:
                    validate_email(email)
                except ValidationError:
                    logger.warning("BulkEnrollView: Invalid email: %s", email)
                    continue
                allowed, created = LearningPathEnrollmentAllowed.objects.get_or_create(
                    email=email, learning_path=learning_path
                )
                if created:
                    enrollment_allowed_created.append(allowed)

        return Response(
            {
                "enrollments_created": len(enrollments_created),
                "enrollment_allowed_created": len(enrollment_allowed_created),
            },
            status=status.HTTP_201_CREATED,
        )


class LearningPathCourseEnrollmentView(APIView):
    """API View to enroll a user in a course that's part of a learning path."""

    permission_classes = [IsAuthenticated, IsAdminOrSelf]

    def _get_enrolled_learning_path(self, learning_path_key_str: str) -> LearningPath:
        """
        Get the learning path and verify the user has access and is enrolled.

        :raises: Http404 if the learning path is not found or the user does not have access.
        """
        return get_object_or_404(
            LearningPath.objects.get_paths_visible_to_user(self.request.user).filter(is_enrolled=True),
            key=learning_path_key_str,
        )

    def post(self, request, learning_path_key_str: str, course_key_str: str):
        """
        Enroll a user in a course that's part of a learning path.

        The user must be enrolled in the learning path, and the course must be a step in the path.
        """
        learning_path = self._get_enrolled_learning_path(learning_path_key_str)
        course_key = CourseKey.from_string(course_key_str)

        if not learning_path.steps.filter(course_key=course_key).exists():
            raise ParseError("The course is not part of this learning path.")

        if enroll_user_in_course(request.user, course_key):
            return Response(
                {"detail": "User successfully enrolled in the course."},
                status=status.HTTP_201_CREATED,
            )
        else:
            raise ParseError("Failed to enroll the user in the course.")
