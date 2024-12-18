"""
Views for LearningPath.
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from learning_paths.api.v1.serializers import (
    LearningPathAsProgramSerializer,
    LearningPathGradeSerializer,
    LearningPathProgressSerializer,
)
from learning_paths.models import LearningPath

from .utils import get_aggregate_progress

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

        progress = get_aggregate_progress(request.user, learning_path)
        required_completion = None
        try:
            grading_criteria = learning_path.grading_criteria
            required_completion = grading_criteria.required_completion
        except ObjectDoesNotExist:
            pass

        data = {
            "learning_path_id": learning_path.uuid,
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

    def get(self, request, learning_path_uuid):
        """
        Fetch learning path grade
        """

        learning_path = get_object_or_404(LearningPath, uuid=learning_path_uuid)

        try:
            grading_criteria = learning_path.grading_criteria
        except ObjectDoesNotExist:
            return Response(
                {"detail": "Grading criteria not found for this learning path."},
                status=status.HTTP_404_NOT_FOUND,
            )

        grade = grading_criteria.calculate_grade(request.user)

        data = {
            "learning_path_id": learning_path_uuid,
            "grade": grade,
            "required_grade": grading_criteria.required_grade,
        }

        serializer = LearningPathGradeSerializer(data=data)
        if serializer.is_valid():
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
