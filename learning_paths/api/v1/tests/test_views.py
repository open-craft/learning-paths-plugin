# pylint: disable=missing-module-docstring,missing-class-docstring
from unittest.mock import patch

from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase, force_authenticate

from learning_paths.api.v1.serializers import (
    LearningPathAsProgramSerializer,
    LearningPathProgressSerializer,
)
from learning_paths.api.v1.tests.factories import (
    AcquiredSkillFactory,
    LearningPathEnrollmentFactory,
    LearningPathFactory,
    LearningPathGradingCriteriaFactory,
    LearningPathStepFactory,
    RequiredSkillFactory,
    UserFactory,
)
from learning_paths.api.v1.views import (
    LearningPathAsProgramViewSet,
    LearningPathUserProgressView,
)
from learning_paths.models import LearningPathEnrollment, LearningPathEnrollmentAllowed


class LearningPathAsProgramTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.learning_paths = LearningPathFactory.create_batch(5)
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
        self.learning_path = LearningPathFactory.create()
        self.grading_criteria = LearningPathGradingCriteriaFactory.create(
            learning_path=self.learning_path,
            required_completion=0.80,
            required_grade=0.75,
        )

    @patch("learning_paths.api.v1.views.get_aggregate_progress", return_value=0.75)
    def test_learning_path_progress_success(
        self, mock_get_aggregate_progress
    ):  # pylint: disable=unused-argument
        """
        Test retrieving progress for a learning path.
        """
        url = reverse("learning-path-progress", args=[self.learning_path.key])
        request = APIRequestFactory().get(url, format="json")
        view = LearningPathUserProgressView.as_view()
        force_authenticate(request, user=self.user)
        response = view(request, learning_path_key_str=str(self.learning_path.key))

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_data = {
            "learning_path_key": str(self.learning_path.key),
            "progress": 0.75,
            "required_completion": 0.80,
        }
        serializer = LearningPathProgressSerializer(data=expected_data)
        serializer.is_valid()
        self.assertEqual(response.data, serializer.data)


class LearningPathUserGradeTests(APITestCase):
    def setUp(self) -> None:
        super().setUp()
        self.staff_user = UserFactory(is_staff=True)
        self.client.force_authenticate(user=self.staff_user)
        self.learning_path = LearningPathFactory.create()
        self.grading_criteria = LearningPathGradingCriteriaFactory.create(
            learning_path=self.learning_path,
            required_completion=0.80,
            required_grade=0.75,
        )

    def test_learning_path_grade_grading_criteria_not_found(self):
        """
        Test that the grade view returns 404 if grading criteria are not found.
        """
        self.grading_criteria.delete()
        url = reverse("learning-path-grade", args=[self.learning_path.key])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            response.data["detail"],
            "Grading criteria not found for this learning path.",
        )

    @patch("learning_paths.api.v1.views.get_aggregate_progress", return_value=80.0)
    @patch(
        "learning_paths.models.LearningPathGradingCriteria.calculate_grade",
        return_value=0.85,
    )
    def test_learning_path_grade_success(
        self, mock_calculate_grade, mock_get_progress
    ):  # pylint: disable=unused-argument
        """
        Test retrieving grade for a learning path.
        """
        url = reverse("learning-path-grade", args=[self.learning_path.key])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["grade"], 0.85)
        self.assertTrue(response.data["required_grade"], 0.75)


class LearningPathViewSetTests(APITestCase):
    def setUp(self) -> None:
        super().setUp()
        self.user = UserFactory()
        self.client.force_authenticate(user=self.user)
        self.learning_paths = LearningPathFactory.create_batch(3)
        for lp in self.learning_paths:
            LearningPathStepFactory.create(
                learning_path=lp, order=1, course_key="course-v1:edX+DemoX+Demo_Course"
            )
            LearningPathStepFactory.create(
                learning_path=lp,
                order=2,
                course_key="course-v1:edX+DemoX+Another_Course",
            )
            RequiredSkillFactory.create(learning_path=lp)
            AcquiredSkillFactory.create(learning_path=lp)

    def test_learning_path_list(self):
        """
        Test that the list endpoint returns all learning paths with basic fields.
        """
        url = reverse("learning-path-list")
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), len(self.learning_paths))
        first_item = response.data[0]
        self.assertIn("key", first_item)
        self.assertIn("slug", first_item)
        self.assertIn("display_name", first_item)

    def test_learning_path_retrieve(self):
        """
        Test that the retrieve endpoint returns the details of a learning path,
        including steps and associated skills.
        """
        lp = self.learning_paths[0]
        url = reverse("learning-path-detail", args=[lp.key])
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("steps", response.data)
        self.assertIn("required_skills", response.data)
        self.assertIn("acquired_skills", response.data)
        if response.data["steps"]:
            first_step = response.data["steps"][0]
            self.assertIn("order", first_step)
            self.assertIn("course_key", first_step)
            self.assertIn("relative_due_date_in_days", first_step)
            self.assertIn("weight", first_step)

    def test_invalid_learning_path_key_returns_404(self):
        """
        Test that an invalid learning path key format returns a 404 response.
        """
        url = reverse("learning-path-detail", args=["invalid-key-format"])
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["detail"], "Invalid learning path key format.")


class LearningPathEnrollmentTests(APITestCase):
    def setUp(self) -> None:
        super().setUp()
        self.staff = UserFactory(is_staff=True)
        self.learner = UserFactory()
        self.another_learner = UserFactory()
        self.learning_path = LearningPathFactory.create()
        self.url = f"/api/learning_paths/v1/{self.learning_path.key}/enrollments/"

    def test_get_with_username_for_staff(self):
        """
        GIVEN `username` query parameter is present
        WHEN the request is made by staff
        THEN return existing active enrollments for `username`.
        """
        LearningPathEnrollmentFactory(
            user=self.learner, learning_path=self.learning_path, is_active=True
        )

        # Test for staff
        self.client.force_authenticate(user=self.staff)
        response = self.client.get(f"{self.url}?username={self.learner.username}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_get_with_username_for_non_staff(self):
        """
        GIVEN `username` query parameter is present
        WHEN the request is made by non-staff
        THEN return active enrollment if username matches the current user, 403 otherwise.
        """
        LearningPathEnrollmentFactory(
            user=self.learner, learning_path=self.learning_path, is_active=True
        )

        # Test for matching username
        self.client.force_authenticate(user=self.learner)
        response = self.client.get(f"{self.url}?username={self.learner.username}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        # Test for non-matching username
        other_user = UserFactory()
        response = self.client.get(self.url, {"username": other_user.username})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_without_username_for_staff(self):
        """
        GIVEN `username` query parameter is missing or empty
        WHEN the request is made by staff
        THEN return all the active enrollments for the learning path.
        """
        enrollment = LearningPathEnrollmentFactory(
            user=self.learner, learning_path=self.learning_path, is_active=True
        )

        # Test when enrollment is active for staff
        self.client.force_authenticate(user=self.staff)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        # Test when enrollment is inactive for staff
        enrollment.is_active = False  # Mark the same enrollment as inactive
        enrollment.save()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_get_without_username_for_non_staff(self):
        """
        GIVEN `username` query parameter is absent
        WHEN the request is made by non-staff
        THEN return active enrollment or empty list
        """
        # No enrollment
        self.client.force_authenticate(user=self.learner)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

        # Active enrollment
        enrollment = LearningPathEnrollmentFactory(
            user=self.learner, learning_path=self.learning_path, is_active=True
        )

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        # Inactive enrollment
        enrollment.is_active = False
        enrollment.save()

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_enroll_current_user_when_username_absent(self):
        """
        GIVEN `username` query parameter is absent
        WHEN the request is made
        THEN enroll the `currentUser` in the given Learning Path successfully.
        """
        self.client.force_authenticate(user=self.learner)
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            LearningPathEnrollmentFactory._meta.model.objects.filter(
                user=self.learner, learning_path=self.learning_path, is_active=True
            ).exists()
        )

    def test_enroll_different_user_when_current_user_is_staff(self):
        """
        GIVEN `username` query parameter is provided and different from the `currentUser`
        WHEN the `currentUser` is staff
        THEN enroll the `username` in the Learning Path.
        """
        self.client.force_authenticate(user=self.staff)
        response = self.client.post(
            self.url, {"username": self.another_learner.username}
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            LearningPathEnrollmentFactory._meta.model.objects.filter(
                user=self.another_learner,
                learning_path=self.learning_path,
                is_active=True,
            ).exists()
        )

    def test_non_staff_user_enrolling_different_user_returns_403(self):
        """
        GIVEN `username` query parameter is provided and different from the `currentUser`
        WHEN the `currentUser` is not staff
        THEN return HTTP 403 Forbidden.
        """
        self.client.force_authenticate(user=self.learner)

        response = self.client.post(
            self.url, {"username": self.another_learner.username}
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_enrollment_returns_404_for_invalid_user_or_learning_path(self):
        """
        GIVEN invalid `username` or `learning_path_id`
        WHEN a POST request is made
        THEN return HTTP 404 Not Found.
        """
        self.client.force_authenticate(user=self.staff)

        # Test invalid username
        response = self.client.post(self.url, {"username": "non-existent-user"})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Test invalid learning_path_id
        url = reverse("learning-path-enrollments", args=["path-v1:this+does+not+exist"])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_enrollment_returns_409_if_already_enrolled(self):
        """
        GIVEN an active enrollment exists for the user and Learning Path
        WHEN a POST request is made
        THEN return HTTP 409 Conflict.
        """
        LearningPathEnrollmentFactory(
            user=self.learner, learning_path=self.learning_path, is_active=True
        )
        self.client.force_authenticate(user=self.learner)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_re_enrollment(self):
        """
        GIVEN an INACTIVE enrollment exists for the user and Learning Path
        WHEN a POST request is made
        THEN returns HTTP 200 with the enrollment now updated and marked active.
        """
        enrollment = LearningPathEnrollmentFactory(
            user=self.learner, learning_path=self.learning_path, is_active=False
        )
        self.client.force_authenticate(user=self.learner)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        enrollment.refresh_from_db()
        self.assertTrue(enrollment.is_active)

    @override_settings(LEARNING_PATHS_ALLOW_SELF_UNENROLLMENT=True)
    def test_self_unenrollment_marks_enrollment_inactive(self):
        """
        GIVEN an active enrollment exists for the current user
        WHEN a DELETE request is made with `LEARNING_PATHS_ALLOW_SELF_UNENROLLMENT=True`
        THEN the enrollment is marked inactive (`is_active=False`).
        """
        enrollment = LearningPathEnrollmentFactory(
            user=self.learner, learning_path=self.learning_path, is_active=True
        )
        self.client.force_authenticate(user=self.learner)

        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        enrollment.refresh_from_db()
        self.assertFalse(enrollment.is_active)  # Check is_active field is now False

    @override_settings(LEARNING_PATHS_ALLOW_SELF_UNENROLLMENT=False)
    def test_self_unenrollment_denied_when_setting_disabled(self):
        """
        GIVEN an active enrollment exists for the current user
        WHEN a DELETE request is made and `LEARNING_PATHS_ALLOW_SELF_UNENROLLMENT=False`
        THEN the request is denied with HTTP 403.
        """
        LearningPathEnrollmentFactory(
            user=self.learner, learning_path=self.learning_path, is_active=True
        )
        self.client.force_authenticate(user=self.learner)

        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @override_settings(LEARNING_PATHS_ALLOW_SELF_UNENROLLMENT=False)
    def test_staff_unenrollment_succeeds_when_setting_disabled(self):
        """
        GIVEN an active enrollment exists for a learner
        WHEN a DELETE request is made by a staff user and `LEARNING_PATHS_ALLOW_SELF_UNENROLLMENT=False`
        THEN the enrollment is marked inactive (`is_active=False`) successfully.

        This is necessary to verify that the setting doesn't affect staff users.
        """
        enrollment = LearningPathEnrollmentFactory(
            user=self.learner, learning_path=self.learning_path, is_active=True
        )
        self.client.force_authenticate(user=self.staff)

        response = self.client.delete(self.url, {"username": self.learner.username})

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        enrollment.refresh_from_db()
        self.assertFalse(enrollment.is_active)  # Check is_active field is now False

    @override_settings(LEARNING_PATHS_ALLOW_SELF_UNENROLLMENT=True)
    def test_non_staff_users_cannot_unenroll_other_learners(self):
        """
        GIVEN an active enrollment exists for the current user
        WHEN a DELETE request is made with `LEARNING_PATHS_ALLOW_SELF_UNENROLLMENT=True`
        THEN the enrollment is marked inactive (`is_active=False`).
        """
        enrollment = LearningPathEnrollmentFactory(
            user=self.learner, learning_path=self.learning_path, is_active=True
        )
        self.client.force_authenticate(user=self.another_learner)

        response = self.client.delete(self.url, {"username": self.learner.username})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        enrollment.refresh_from_db()
        self.assertTrue(enrollment.is_active)

    @override_settings(LEARNING_PATHS_ALLOW_SELF_UNENROLLMENT=True)
    def test_return_404_when_no_active_enrollments_exist(self):
        """
        GIVEN no active enrollment exists for the user in the learning path
        WHEN a DELETE request is made
        THEN HTTP 404 Not Found is returned.
        """
        # Create an inactive enrollment
        LearningPathEnrollmentFactory(
            user=self.learner, learning_path=self.learning_path, is_active=False
        )
        self.client.force_authenticate(user=self.learner)

        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class TestListEnrollmentsView(APITestCase):
    """
    Unit tests for FetchEnrollmentsView.
    """

    def setUp(self):
        """
        Set up the test data.
        """
        self.user = UserFactory()
        self.staff = UserFactory(is_staff=True)
        self.superuser = UserFactory(is_staff=True, is_superuser=True)
        self.enrollment1 = LearningPathEnrollmentFactory(user=self.user)
        self.enrollment2 = LearningPathEnrollmentFactory(user=self.user)
        self.other_enrollment = LearningPathEnrollmentFactory()
        self.url = "/api/learning_paths/v1/enrollments/"

    def test_fetch_enrollments_as_non_staff_user(self):
        """
        GIVEN enrollments exist for a non-staff user
        WHEN the user is authenticated
        THEN return only the enrollments for the user.
        """
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            len(response.data), 2
        )  # Should return only the user's enrollments
        self.assertEqual(response.data[0]["user"], self.user.id)

    def test_fetch_enrollments_as_staff_or_superuser(self):
        """
        GIVEN there are enrollments
        WHEN the user is authenticated as staff or superuser
        THEN return all enrollments.
        """
        # Superuser
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 3)

        # Staff
        self.client.force_authenticate(user=self.staff)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 3)

    def test_fetch_enrollments_no_enrollments(self):
        """
        GIVEN there are no enrollments
        WHEN the user is authenticated
        THEN return an empty list.
        """
        user_with_no_enrollments = UserFactory()
        self.client.force_authenticate(user=user_with_no_enrollments)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)  # No enrollments should be returned


class BulkEnrollAPITestCase(APITestCase):
    def setUp(self):
        self.regular_user = UserFactory()
        self.admin_user = UserFactory(is_staff=True, is_superuser=True)
        self.client.force_authenticate(user=self.admin_user)

        self.learning_path1 = LearningPathFactory()
        self.learning_path2 = LearningPathFactory()

        self.user1 = UserFactory(email="user1@example.com")
        self.user2 = UserFactory(email="user2@example.com")
        self.url = "/api/learning_paths/v1/enrollments/bulk-enroll/"

    def _call_api(self, payload):
        return self.client.post(self.url, payload, format="json")

    def test_bulk_enrollment_success(self):
        """
        GIVEN valid payload from staff user
        WHEN then keys and emails are valid
        THEN create necessary enrollments and enrollment allowed objects.
        """
        payload = {
            "learning_paths": f"{self.learning_path1.key},{self.learning_path2.key}",
            "emails": "user1@example.com,user2@example.com,new_user@example.com",
        }
        response = self._call_api(payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data["enrollments_created"], 4
        )  # 2 users x 2 learning paths
        self.assertEqual(
            response.data["enrollment_allowed_created"], 2
        )  # (1 non-existing user x 2 learning paths)

        # Check learning path enrollments
        self.assertEqual(
            LearningPathEnrollment.objects.filter(user=self.user1).count(), 2
        )
        self.assertEqual(
            LearningPathEnrollment.objects.filter(user=self.user2).count(), 2
        )

        # Check learning path enrollment allowed
        self.assertEqual(
            set(
                LearningPathEnrollmentAllowed.objects.filter(
                    learning_path=self.learning_path1
                ).values_list("email", flat=True)
            ),
            {"new_user@example.com"},
        )
        self.assertEqual(
            set(
                LearningPathEnrollmentAllowed.objects.filter(
                    learning_path=self.learning_path2
                ).values_list("email", flat=True)
            ),
            {"new_user@example.com"},
        )

    def test_bulk_enrollment_with_invalid_learning_path(self):
        """
        GIVEN valid payload from staff user
        WHEN the learning path key is invalid
        THEN no enrollments are created.
        """
        payload = {
            "learning_paths": "invalid-path-key",
            "emails": "user1@example.com,user2@example.com",
        }
        response = self._call_api(payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["enrollments_created"], 0)
        self.assertEqual(response.data["enrollment_allowed_created"], 0)

    def test_bulk_enrollment_with_invalid_and_valid_emails(self):
        """
        GIVEN valid payload from staff user
        WHEN an email is invalid
        THEN no enrollments are created for the invalid email.
        """
        payload = {
            "learning_paths": f"{self.learning_path1.key}",
            "emails": "user1@example.com,invalid_email",
        }
        response = self._call_api(payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["enrollments_created"], 1)
        self.assertEqual(response.data["enrollment_allowed_created"], 0)

        # Check learning path enrollment for valid user
        self.assertTrue(
            LearningPathEnrollment.objects.filter(
                user=self.user1, learning_path=self.learning_path1
            ).exists()
        )

        # Check enrollment allowed for invalid email doesn't exist
        self.assertFalse(
            LearningPathEnrollmentAllowed.objects.filter(
                email="invalid_email", learning_path=self.learning_path1
            ).exists()
        )

    def test_bulk_enrollment_unauthenticated(self):
        """
        GIVEN the user is not authenticated, or is not an staff
        WHEN an API request is made
        THEN a 403 is returned.
        """
        self.client.logout()
        payload = {
            "learning_paths": f"{self.learning_path1.key}",
            "emails": "user1@example.com",
        }
        # Un-authenticates
        response = self._call_api(payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Non-staff user
        self.client.force_login(self.regular_user)
        response = self._call_api(payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_bulk_enrollment_returned_counts_reflect_only_new_ones(self):
        """
        GIVEN there is existing enrollment or enrollment allowed objects
        WHEN request is made for the same users and learning paths
        THEN no duplicates are created and the count reflects only new ones.
        """
        LearningPathEnrollmentFactory(
            learning_path=self.learning_path1, user=self.user1, is_active=True
        )

        payload = {
            "learning_paths": f"{self.learning_path1.key}",
            "emails": self.user1.email,
        }

        response = self._call_api(payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["enrollments_created"], 0)
        self.assertEqual(response.data["enrollment_allowed_created"], 0)

    def test_re_enrollment(self):
        """
        GIVEN there is an existing INACTIVE enrollment for a learner
        WHEN request is made for the same user and learning path
        THEN the existing enrollment is make active.
        """
        LearningPathEnrollmentFactory(
            learning_path=self.learning_path1, user=self.user1, is_active=False
        )

        payload = {
            "learning_paths": f"{self.learning_path1.key}",
            "emails": self.user1.email,
        }

        response = self._call_api(payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["enrollments_created"], 1)
