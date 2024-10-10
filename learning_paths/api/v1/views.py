"""
Views for LearningPath.
"""
from django.http import JsonResponse
from rest_framework import viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated

from learning_paths.api.v1.serializers import LearningPathAsProgramSerializer
from learning_paths.models import LearningPath
from .utils import get_aggregate_progress

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


def learning_path_progress_view(request, learning_path_id):
    """
    API view to return the aggregate progress of a user in a learning path.
    """
    try:
        learning_path = LearningPath.objects.get(id=learning_path_id)
    except LearningPath.DoesNotExist:
        return JsonResponse({'error': 'Learning Path not found'}, status=404)

    aggregate_progress = get_aggregate_progress(request, learning_path)

    return JsonResponse({'learning_path_id': learning_path_id, 'aggregate_progress': aggregate_progress})
