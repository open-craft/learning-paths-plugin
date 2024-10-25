# pylint: disable=missing-module-docstring,missing-class-docstring
from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase, force_authenticate

from learning_paths.api.v1.serializers import (
    LearningPathAsProgramSerializer,
    LearningPathProgressSerializer,
)
from learning_paths.api.v1.tests.factories import LearnerPathwayFactory, UserFactory
from learning_paths.api.v1.views import (
    LearningPathAsProgramViewSet,
    LearningPathUserProgressView,
)


class LearningPathAsProgramTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.learning_paths = LearnerPathwayFactory.create_batch(5)
        self.user = UserFactory()
        self.client.force_authenticate(user=self.user)

    def test_list_learning_paths_as_programs(self):
        """
        Test listing LearningPaths as Programs.
        """
        url = reverse("learning-path-as-program-list")
        request = APIRequestFactory().get(url, format="json")
        view = LearningPathAsProgramViewSet.as_view({"get": "list"})
        force_authenticate(request, user=self.user)
        response = view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        serializer = LearningPathAsProgramSerializer(self.learning_paths, many=True)
        self.assertEqual(response.data, serializer.data)


class LearningPathUserProgressTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.user = UserFactory()
        self.client.force_authenticate(user=self.user)
        self.learning_path = LearnerPathwayFactory.create()

    @patch("learning_paths.api.v1.views.get_aggregate_progress")
    def test_learning_path_progress_success(self, mock_get_aggregate_progress):
        """
        Test retrieving progress for a learning path.
        """
        mock_get_aggregate_progress.return_value = 0.75

        url = reverse("learning-path-progress", args=[self.learning_path.uuid])
        request = APIRequestFactory().get(url, format="json")
        view = LearningPathUserProgressView.as_view()
        force_authenticate(request, user=self.user)
        response = view(request, learning_path_uuid=self.learning_path.uuid)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_data = {
            "learning_path_id": str(self.learning_path.uuid),
            "aggregate_progress": 0.75,
        }
        serializer = LearningPathProgressSerializer(data=expected_data)
        serializer.is_valid()
        self.assertEqual(response.data, serializer.data)
