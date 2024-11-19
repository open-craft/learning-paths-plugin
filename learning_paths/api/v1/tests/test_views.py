# pylint: disable=missing-module-docstring,missing-class-docstring
from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase, force_authenticate

from learning_paths.api.v1.serializers import (
    LearningPathAsProgramSerializer,
    LearningPathProgressSerializer,
)
from learning_paths.api.v1.tests.factories import (
    LearnerPathGradingCriteriaFactory,
    LearnerPathwayFactory,
    UserFactory,
)
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

    @patch("learning_paths.api.v1.views.get_aggregate_progress", return_value=0.75)
    def test_learning_path_progress_success(
        self, mock_get_aggregate_progress
    ):  # pylint: disable=unused-argument
        """
        Test retrieving progress for a learning path.
        """
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


class LearningPathUserGradeTests(APITestCase):
    def setUp(self) -> None:
        super().setUp()
        self.staff_user = UserFactory(is_staff=True)
        self.regular_user = UserFactory()
        self.client.force_authenticate(user=self.staff_user)
        self.learning_path = LearnerPathwayFactory.create()
        self.grading_criteria = LearnerPathGradingCriteriaFactory.create(
            learning_path=self.learning_path,
            completion_threshold=100.0,
            expected_grade=75.0,
        )

    def test_learning_path_grade_permission_denied_for_non_staff(self):
        """
        Test that non-staff users cannot access the grade view.
        """
        self.client.force_authenticate(user=self.regular_user)
        url = reverse("learning-path-grade", args=[self.learning_path.uuid])
        response = self.client.get(url, {"username": self.regular_user.username})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_learning_path_grade_missing_username_param(self):
        """
        Test that the grade view returns 400 if the username parameter is missing.
        """
        url = reverse("learning-path-grade", args=[self.learning_path.uuid])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "Username parameter is required.")

    def test_learning_path_grade_grading_criteria_not_found(self):
        """
        Test that the grade view returns 404 if grading criteria are not found.
        """
        self.grading_criteria.delete()
        url = reverse("learning-path-grade", args=[self.learning_path.uuid])
        response = self.client.get(url, {"username": self.staff_user.username})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            response.data["detail"],
            "Grading criteria not found for this learning path.",
        )

    @patch(
        "learning_paths.api.v1.views.calculate_learning_path_grade", return_value=85.0
    )
    @patch("learning_paths.api.v1.views.is_learning_path_completed", return_value=True)
    def test_learning_path_grade_success(
        self, mock_is_completed, mock_calculate_grade
    ):  # pylint: disable=unused-argument
        """
        Test retrieving grade for a learning path.
        """
        url = reverse("learning-path-grade", args=[self.learning_path.uuid])
        response = self.client.get(url, {"username": self.staff_user.username})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["aggregate_grade"], 85.0)
        self.assertTrue(response.data["is_completed"])
        self.assertTrue(response.data["meets_expected_grade"])
