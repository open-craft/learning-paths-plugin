"""
Views for LearningPath.
"""

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from learning_paths.api.v1.serializers import (
    LearningPathAsProgramSerializer,
    LearningPathProgressSerializer,
)
from learning_paths.models import LearningPath, LearningPathGradingCriteria

from .utils import (
    calculate_learning_path_grade,
    get_aggregate_progress,
    is_learning_path_completed,
)

User = get_user_model()


class LearningPathAsProgramViewSet(viewsets.ReadOnlyModelViewSet):
    """
    This viewset exposes LearningPaths as Programs to be ingested
    by the course-discovery's refresh_course_metadata command.
    URL is: GET <LMS_URL>/api/v1/programs
    The command makes use of the ProgramsApiDataLoader.
    https://github.com/openedx/course-discovery/blob/d6a57fd69479b3d5f5afb682d2668b58503a6af6/course_discovery/apps/course_metadata/data_loaders/api.py#L843
    """

    queryset = LearningPath.objects.all()
    permission_classes = (IsAuthenticated,)
    serializer_class = LearningPathAsProgramSerializer
    pagination_class = PageNumberPagination


class LearningPathUserProgressView(APIView):
    """
    API view to return the aggregate progress of a user in a learning path.
    """

    permission_classes = (IsAuthenticated,)

    def get(self, request, learning_path_uuid):
        """
        Fetch the learning path progress
        """
        learning_path = get_object_or_404(LearningPath, uuid=learning_path_uuid)

        aggregate_progress = get_aggregate_progress(request.user, learning_path)

        data = {
            "learning_path_id": learning_path.uuid,
            "aggregate_progress": aggregate_progress,
        }

        serializer = LearningPathProgressSerializer(data=data)
        if serializer.is_valid():
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LearningPathUserGradeView(APIView):
    """
    API view to return the aggregate grade of a user in a learning path.
    Only accessible by staff users.
    """

    permission_classes = (IsAuthenticated,)

    def get(self, request, learning_path_uuid):
        """
        Fetch learning path grade
        """
        if not request.user.is_staff:
            return Response(
                {"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN
            )

        username = request.query_params.get("username")
        if not username:
            return Response(
                {"detail": "Username parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = get_object_or_404(User, username=username)

        learning_path = get_object_or_404(LearningPath, uuid=learning_path_uuid)

        try:
            grading_criteria = LearningPathGradingCriteria.objects.get(
                learning_path=learning_path
            )
        except LearningPathGradingCriteria.DoesNotExist:
            return Response(
                {"detail": "Grading criteria not found for this learning path."},
                status=status.HTTP_404_NOT_FOUND,
            )

        is_completed = is_learning_path_completed(user, learning_path)
        aggregate_grade = calculate_learning_path_grade(user, learning_path)
        meets_expected_grade = aggregate_grade >= grading_criteria.expected_grade

        data = {
            "username": username,
            "learning_path_id": learning_path_uuid,
            "is_completed": is_completed,
            "aggregate_grade": aggregate_grade,
            "meets_expected_grade": meets_expected_grade,
        }

        return Response(data, status=status.HTTP_200_OK)
