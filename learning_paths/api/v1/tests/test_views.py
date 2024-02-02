# pylint: disable=missing-module-docstring,missing-class-docstring
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase, force_authenticate

from learning_paths.api.v1.serializers import LearningPathAsProgramSerializer
from learning_paths.api.v1.tests.factories import LearnerPathwayFactory, UserFactory
from learning_paths.api.v1.views import LearningPathAsProgramViewSet


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
