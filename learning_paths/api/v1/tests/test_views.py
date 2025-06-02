# pylint: disable=missing-module-docstring,missing-class-docstring,redefined-outer-name,unused-argument
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate

from learning_paths.api.v1.serializers import (
    LearningPathAsProgramSerializer,
    LearningPathProgressSerializer,
)
from learning_paths.api.v1.views import (
    LearningPathAsProgramViewSet,
    LearningPathUserProgressView,
)
from learning_paths.models import (
    LearningPathEnrollment,
    LearningPathEnrollmentAllowed,
    LearningPathEnrollmentAudit,
)
from learning_paths.tests.factories import (
    AcquiredSkillFactory,
    LearningPathEnrollmentAllowedFactory,
    LearningPathEnrollmentFactory,
    LearningPathFactory,
    LearningPathStepFactory,
    RequiredSkillFactory,
    UserFactory,
)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def staff_user():
    return UserFactory(is_staff=True)


@pytest.fixture
def superuser():
    return UserFactory(is_staff=True, is_superuser=True)


@pytest.fixture
def authenticated_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def staff_client(api_client, staff_user):
    api_client.force_authenticate(user=staff_user)
    return api_client


@pytest.fixture
def superuser_client(api_client, superuser):
    api_client.force_authenticate(user=superuser)
    return api_client


@pytest.fixture
def learning_paths():
    return LearningPathFactory.create_batch(5, invite_only=False)


@pytest.fixture
def learning_path_with_steps(
    learning_path,
):  # pylint: disable=missing-function-docstring
    LearningPathStepFactory.create(
        learning_path=learning_path,
        order=1,
        course_key="course-v1:edX+DemoX+Demo_Course",
    )
    LearningPathStepFactory.create(
        learning_path=learning_path,
        order=2,
        course_key="course-v1:edX+DemoX+Another_Course",
    )
    RequiredSkillFactory.create(learning_path=learning_path)
    AcquiredSkillFactory.create(learning_path=learning_path)
    return learning_path


@pytest.fixture
def learning_paths_with_steps():  # pylint: disable=missing-function-docstring
    learning_paths = LearningPathFactory.create_batch(3, invite_only=False)
    for lp in learning_paths:
        LearningPathStepFactory.create(learning_path=lp, order=1, course_key="course-v1:edX+DemoX+Demo_Course")
        LearningPathStepFactory.create(learning_path=lp, order=2, course_key="course-v1:edX+DemoX+Another_Course")
        RequiredSkillFactory.create(learning_path=lp)
        AcquiredSkillFactory.create(learning_path=lp)
    return learning_paths


@pytest.mark.django_db
class TestLearningPathAsProgram:

    def test_list_learning_paths_as_programs(self, user, learning_paths):
        """Test listing LearningPaths as Programs."""
        url = reverse("learning-path-as-program-list")
        request = APIRequestFactory().get(url)
        view = LearningPathAsProgramViewSet.as_view({"get": "list"})
        force_authenticate(request, user=user)
        response = view(request)

        assert response.status_code == status.HTTP_200_OK

        serializer = LearningPathAsProgramSerializer(learning_paths, many=True)
        assert response.data == serializer.data


@pytest.mark.django_db
class TestLearningPathUserProgress:

    @patch("learning_paths.api.v1.views.get_aggregate_progress", return_value=0.75)
    def test_learning_path_progress_success(self, _mock_get_aggregate_progress, user, learning_path):
        """Test retrieving progress for a learning path."""
        url = reverse("learning-path-progress", args=[learning_path.key])
        request = APIRequestFactory().get(url)
        view = LearningPathUserProgressView.as_view()
        force_authenticate(request, user=user)
        response = view(request, learning_path_key_str=str(learning_path.key))

        assert response.status_code == status.HTTP_200_OK

        expected_data = {
            "learning_path_key": str(learning_path.key),
            "progress": 0.75,
            "required_completion": 0.80,
        }
        serializer = LearningPathProgressSerializer(data=expected_data)
        serializer.is_valid()
        assert response.data == serializer.data

    def test_learning_path_progress_not_found(self, authenticated_client):
        """Test that the progress view returns 404 if the learning path is not found."""
        url = reverse("learning-path-progress", args=["path-v1:this+does+not+exist"])
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_invite_only_learning_path_progress_404(self, authenticated_client, learning_path_with_invite_only):
        """Test that the progress view returns 404 if the learning path is invite-only."""
        url = reverse("learning-path-progress", args=[learning_path_with_invite_only.key])
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestLearningPathUserGrade:

    def test_learning_path_grade_grading_criteria_not_found(self, authenticated_client, learning_path):
        """Test that the grade view returns 404 if grading criteria are not found."""
        learning_path.grading_criteria.delete()
        url = reverse("learning-path-grade", args=[learning_path.key])
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["detail"] == "Grading criteria not found for this learning path."

    @patch("learning_paths.api.v1.views.get_aggregate_progress", return_value=80.0)
    @patch(
        "learning_paths.models.LearningPathGradingCriteria.calculate_grade",
        return_value=0.85,
    )
    def test_learning_path_grade_success(
        self,
        _mock_calculate_grade,
        _mock_get_progress,
        authenticated_client,
        learning_path,
    ):
        """Test retrieving grade for a learning path."""
        url = reverse("learning-path-grade", args=[learning_path.key])
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["grade"] == 0.85
        assert response.data["required_grade"] == 0.75

    def test_learning_path_grade_not_found(self, authenticated_client):
        """Test that the grade view returns 404 if the learning path is not found."""
        url = reverse("learning-path-grade", args=["path-v1:this+does+not+exist"])
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_invite_only_learning_path_grade_404(self, authenticated_client, learning_path_with_invite_only):
        """Test that the grade view returns 404 if the learning path is invite-only."""
        url = reverse("learning-path-grade", args=[learning_path_with_invite_only.key])
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestLearningPathViewSet:

    @pytest.fixture(autouse=True)
    def setup_mock_course_dates(self):
        """Mock course dates that are retrieved from edx-platform."""
        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        with patch("learning_paths.models.get_course_dates", return_value=(start_date, end_date)):
            yield

    def test_learning_path_list(self, authenticated_client, learning_paths_with_steps):
        """Test that the list endpoint returns all learning paths with basic fields."""
        url = reverse("learning-path-list")
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == len(learning_paths_with_steps)
        first_item = response.data[0]
        assert "key" in first_item
        assert "display_name" in first_item
        assert "steps" in first_item
        assert "enrollment_date" in first_item
        assert first_item["enrollment_date"] is None

    def test_learning_path_retrieve(self, authenticated_client, learning_paths_with_steps):
        """Test that the retrieve endpoint returns the details of a learning path."""
        lp = learning_paths_with_steps[0]
        url = reverse("learning-path-detail", args=[lp.key])

        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert "steps" in response.data
        assert "required_skills" in response.data
        assert "acquired_skills" in response.data
        assert "enrollment_date" in response.data
        assert response.data["enrollment_date"] is None

        if response.data["steps"]:
            first_step = response.data["steps"][0]
            assert "order" in first_step
            assert "course_key" in first_step
            assert "course_dates" in first_step
            assert "weight" in first_step

    def test_invalid_learning_path_key_returns_404(self, authenticated_client):
        """Test that an invalid learning path key format returns a 404 response."""
        url = reverse("learning-path-detail", args=["invalid-key-format"])
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["detail"] == "Invalid learning path key format."

    def test_non_existent_learning_path_returns_404(self, authenticated_client):
        """Test that a non-existent learning path key returns a 404 response."""
        url = reverse("learning-path-detail", args=["path-v1:this+does+not+exist"])
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["detail"] == "No LearningPath matches the given query."

    def test_learning_path_list_with_enrollment(self, authenticated_client, active_enrollment, user):
        """Test that the list endpoint returns all learning paths with enrollment status."""
        url = reverse("learning-path-list")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        first_item = response.data[0]
        assert "enrollment_date" in first_item
        assert first_item["enrollment_date"] is not None

    def test_learning_path_retrieve_with_enrollment(self, authenticated_client, active_enrollment, learning_path, user):
        """Test that the retrieve endpoint returns the details of a learning path with enrollment status."""
        url = reverse("learning-path-detail", args=[learning_path.key])
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "enrollment_date" in response.data
        assert response.data["enrollment_date"] is not None

    def test_learning_path_retrieve_with_inactive_enrollment(
        self, authenticated_client, inactive_enrollment, learning_path, user
    ):
        """Test that the retrieve endpoint returns the details of a learning path with inactive enrollment status."""
        url = reverse("learning-path-detail", args=[learning_path.key])
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "enrollment_date" in response.data
        assert response.data["enrollment_date"] is None

    def test_invite_only_learning_paths_hidden_from_non_enrolled_users(
        self, authenticated_client, learning_path_with_invite_only, learning_path
    ):
        """Test that invite-only learning paths are hidden from non-enrolled users."""
        url = reverse("learning-path-list")
        response = authenticated_client.get(url)

        # Only the public path should be visible
        assert len(response.data) == 1
        assert response.data[0]["key"] == str(learning_path.key)

    def test_invite_only_learning_paths_visible_to_enrolled_users(
        self, authenticated_client, user, learning_path_with_invite_only
    ):
        """Test that invite-only learning paths are visible to enrolled users."""
        LearningPathEnrollmentFactory(user=user, learning_path=learning_path_with_invite_only, is_active=True)

        url = reverse("learning-path-list")
        response = authenticated_client.get(url)

        assert len(response.data) == 1
        assert response.data[0]["key"] == str(learning_path_with_invite_only.key)

    def test_invite_only_learning_paths_visible_to_staff(self, staff_client, learning_path_with_invite_only):
        """Test that invite-only learning paths are visible to staff users."""
        url = reverse("learning-path-list")
        response = staff_client.get(url)

        assert len(response.data) == 1
        assert response.data[0]["key"] == str(learning_path_with_invite_only.key)

    def test_invite_only_learning_path_detail_hidden_from_non_enrolled_users(
        self, authenticated_client, user, learning_path_with_invite_only
    ):
        """Test that invite-only learning path details are hidden from non-enrolled users."""
        url = reverse("learning-path-detail", args=[learning_path_with_invite_only.key])
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        # Ensure the message is identical to the non-existent learning path case.
        assert response.data["detail"] == "No LearningPath matches the given query."


@pytest.mark.django_db
class TestLearningPathEnrollment:

    @pytest.fixture
    def enrollment_url(self, learning_path):
        return f"/api/learning_paths/v1/{learning_path.key}/enrollments/"

    @pytest.fixture
    def another_user(self):
        return UserFactory()

    def test_get_with_username_for_staff(self, staff_client, user, active_enrollment, enrollment_url):
        """Test staff can view enrollments for a specific user."""
        response = staff_client.get(f"{enrollment_url}?username={user.username}")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1

    def test_get_with_username_for_non_staff(self, user, authenticated_client, active_enrollment, enrollment_url):
        """Test non-staff can only view their own enrollments."""
        # Test for matching username
        response = authenticated_client.get(f"{enrollment_url}?username={user.username}")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1

        # Test for non-matching username
        other_user = UserFactory()
        response = authenticated_client.get(f"{enrollment_url}?username={other_user.username}")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_without_username_for_staff(self, staff_client, active_enrollment, enrollment_url):
        """Test staff can view all enrollments for a learning path."""
        # Test when enrollment is active for staff
        response = staff_client.get(enrollment_url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1

        # Test when enrollment is inactive for staff
        active_enrollment.is_active = False
        active_enrollment.save()
        response = staff_client.get(enrollment_url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 0

    def test_get_without_username_for_non_staff(self, authenticated_client, user, learning_path, enrollment_url):
        """Test non-staff get their own enrollments for a learning path."""
        # No enrollment
        response = authenticated_client.get(enrollment_url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data == []

        # Active enrollment
        enrollment = LearningPathEnrollmentFactory(user=user, learning_path=learning_path, is_active=True)
        response = authenticated_client.get(enrollment_url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1

        # Inactive enrollment
        enrollment.is_active = False
        enrollment.save()
        response = authenticated_client.get(enrollment_url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data == []

    def test_enroll_current_user_when_username_absent(self, authenticated_client, user, learning_path, enrollment_url):
        """Test user can enroll themselves when username is absent."""
        response = authenticated_client.post(enrollment_url)
        assert response.status_code == status.HTTP_201_CREATED
        assert LearningPathEnrollment.objects.filter(user=user, learning_path=learning_path, is_active=True).exists()

    def test_enroll_different_user_when_current_user_is_staff(
        self, staff_client, another_user, learning_path, enrollment_url
    ):
        """Test staff can enroll other users."""
        response = staff_client.post(enrollment_url, {"username": another_user.username})
        assert response.status_code == status.HTTP_201_CREATED
        assert LearningPathEnrollment.objects.filter(
            user=another_user, learning_path=learning_path, is_active=True
        ).exists()

    def test_non_staff_user_enrolling_different_user_returns_403(
        self, authenticated_client, another_user, enrollment_url
    ):
        """Test non-staff cannot enroll other users."""
        response = authenticated_client.post(enrollment_url, {"username": another_user.username})
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.parametrize("http_method", ["get", "post", "delete"])
    def test_invite_only_learning_path_returns_404_for_non_enrolled_users(
        self, authenticated_client, user, learning_path_with_invite_only, http_method
    ):
        """Test that invite-only learning paths return 404 for non-enrolled users."""
        url = f"/api/learning_paths/v1/{learning_path_with_invite_only.key}/enrollments/"

        request_method = getattr(authenticated_client, http_method)
        response = request_method(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["detail"] == "No LearningPath matches the given query."

    def test_enrollment_returns_404_for_invalid_user_or_learning_path(self, staff_client, learning_path):
        """Test enrollment with an invalid username or learning path returns 404."""
        # Test invalid username
        url = f"/api/learning_paths/v1/{learning_path.key}/enrollments/"
        response = staff_client.post(url, {"username": "non-existent-user"})
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["detail"] == "No User matches the given query."

        # Test invalid learning_path_id
        url = reverse("learning-path-enrollments", args=["path-v1:this+does+not+exist"])
        response = staff_client.post(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["detail"] == "No LearningPath matches the given query."

    def test_enrollment_returns_409_if_already_enrolled(self, authenticated_client, active_enrollment, enrollment_url):
        """Test enrollment returns conflict if user is already enrolled."""
        response = authenticated_client.post(enrollment_url)
        assert response.status_code == status.HTTP_409_CONFLICT

    def test_re_enrollment(self, authenticated_client, inactive_enrollment, enrollment_url):
        """Test re-enrolling a user with inactive enrollment updates to active."""
        response = authenticated_client.post(enrollment_url)
        assert response.status_code == status.HTTP_200_OK
        inactive_enrollment.refresh_from_db()
        assert inactive_enrollment.is_active is True

    @override_settings(LEARNING_PATHS_ALLOW_SELF_UNENROLLMENT=True)
    def test_self_unenrollment_marks_enrollment_inactive(self, authenticated_client, active_enrollment, enrollment_url):
        """Test self-unenrollment marks enrollment inactive when the setting is enabled."""
        response = authenticated_client.delete(enrollment_url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        active_enrollment.refresh_from_db()
        assert active_enrollment.is_active is False

    @override_settings(LEARNING_PATHS_ALLOW_SELF_UNENROLLMENT=False)
    def test_self_unenrollment_denied_when_setting_disabled(
        self, authenticated_client, active_enrollment, enrollment_url
    ):
        """Test self-unenrollment is denied when setting is disabled."""
        response = authenticated_client.delete(enrollment_url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @override_settings(LEARNING_PATHS_ALLOW_SELF_UNENROLLMENT=False)
    def test_staff_unenrollment_succeeds_when_setting_disabled(
        self, staff_client, user, active_enrollment, enrollment_url
    ):
        """Test staff can still unenroll users even when self-unenrollment is disabled."""
        response = staff_client.delete(enrollment_url, {"username": user.username})
        assert response.status_code == status.HTTP_204_NO_CONTENT
        active_enrollment.refresh_from_db()
        assert active_enrollment.is_active is False

    @override_settings(LEARNING_PATHS_ALLOW_SELF_UNENROLLMENT=True)
    def test_non_staff_users_cannot_unenroll_other_learners(  # pylint: disable=too-many-positional-arguments
        self, api_client, user, another_user, active_enrollment, enrollment_url
    ):
        """Test non-staff cannot unenroll other users."""
        api_client.force_authenticate(user=another_user)
        response = api_client.delete(enrollment_url, {"username": user.username})
        assert response.status_code == status.HTTP_403_FORBIDDEN
        active_enrollment.refresh_from_db()
        assert active_enrollment.is_active is True

    @override_settings(LEARNING_PATHS_ALLOW_SELF_UNENROLLMENT=True)
    def test_return_404_when_no_active_enrollments_exist(
        self, authenticated_client, inactive_enrollment, enrollment_url
    ):
        """Test unenrollment returns 404 when no active enrollment exists."""
        response = authenticated_client.delete(enrollment_url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_self_enrollment_denied_for_invite_only_learning_path(
        self, authenticated_client, user, learning_path_with_invite_only
    ):
        """Test that users cannot self-enroll in invite-only learning paths."""
        url = reverse("learning-path-enrollments", args=[learning_path_with_invite_only.key])
        response = authenticated_client.post(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

        assert not LearningPathEnrollment.objects.filter(
            user=user, learning_path=learning_path_with_invite_only
        ).exists()

    def test_self_enrollment_allowed_for_non_invite_only_learning_path(self, authenticated_client, user, learning_path):
        """Test that users can self-enroll in non-invite-only learning paths."""
        url = reverse("learning-path-enrollments", args=[learning_path.key])
        response = authenticated_client.post(url)

        assert response.status_code == status.HTTP_201_CREATED

        assert LearningPathEnrollment.objects.filter(user=user, learning_path=learning_path, is_active=True).exists()

    def test_staff_can_enroll_users_in_invite_only_learning_path(
        self, staff_client, another_user, learning_path_with_invite_only
    ):
        """Test that staff can enroll users in invite-only learning paths."""
        url = reverse("learning-path-enrollments", args=[learning_path_with_invite_only.key])
        response = staff_client.post(url, {"username": another_user.username})

        assert response.status_code == status.HTTP_201_CREATED

        assert LearningPathEnrollment.objects.filter(
            user=another_user,
            learning_path=learning_path_with_invite_only,
            is_active=True,
        ).exists()


@pytest.mark.django_db
class TestListEnrollmentsView:

    @pytest.fixture
    def enrollments_url(self):
        return "/api/learning_paths/v1/enrollments/"

    @pytest.fixture(autouse=True)
    def user_with_enrollments(self):  # pylint: disable=missing-function-docstring
        test_user = UserFactory()
        LearningPathEnrollmentFactory(user=test_user)
        LearningPathEnrollmentFactory(user=test_user)
        LearningPathEnrollmentFactory()
        return test_user

    def test_fetch_enrollments_as_non_staff_user(self, authenticated_client, user_with_enrollments, enrollments_url):
        """Test non-staff user can only fetch their own enrollments."""
        authenticated_client.force_authenticate(user=user_with_enrollments)
        response = authenticated_client.get(enrollments_url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2
        assert response.data[0]["user"] == user_with_enrollments.id

    def test_fetch_enrollments_as_staff_or_superuser(self, staff_client, superuser_client, enrollments_url):
        """Test staff and superusers can fetch all enrollments."""
        # Superuser
        response = superuser_client.get(enrollments_url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 3

        # Staff
        response = staff_client.get(enrollments_url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 3

    def test_fetch_enrollments_no_enrollments(self, api_client, enrollments_url):
        """Test user with no enrollments gets an empty list."""
        user_with_no_enrollments = UserFactory()
        api_client.force_authenticate(user=user_with_no_enrollments)
        response = api_client.get(enrollments_url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 0


@pytest.mark.django_db
class TestBulkEnrollAPI:

    @pytest.fixture
    def bulk_enroll_url(self):
        return "/api/learning_paths/v1/enrollments/bulk-enroll/"

    def test_bulk_enrollment_success(self, staff_client, staff_user, bulk_enroll_url):
        """Test bulk enrollment creates enrollments and enrollment allowed objects and their audits."""
        payload = {
            "learning_paths": f"{LearningPathFactory().key},{LearningPathFactory().key}",
            "emails": f"{UserFactory().email},{UserFactory().email},new_user@example.com",
            "reason": "TestReason",
            "org": "TestOrg",
            "role": "TestRole",
        }
        response = staff_client.post(bulk_enroll_url, payload)

        assert response.status_code == status.HTTP_201_CREATED
        # 2 users x 2 learning paths
        assert response.data["enrollments_created"] == 4
        # (1 non-existing user x 2 learning paths)
        assert response.data["enrollment_allowed_created"] == 2

        all_audits = list(LearningPathEnrollmentAudit.objects.all())
        assert len(all_audits) == 6

        for audit in all_audits:
            if audit.enrollment:
                assert audit.state_transition == LearningPathEnrollmentAudit.UNENROLLED_TO_ENROLLED
            else:
                assert audit.state_transition == LearningPathEnrollmentAudit.UNENROLLED_TO_ALLOWEDTOENROLL

            assert audit.enrolled_by == staff_user
            assert audit.reason == payload["reason"]
            assert audit.org == payload["org"]
            assert audit.role == payload["role"]

    def test_bulk_enrollment_updates_existing_enrollment_allowed(self, staff_client, bulk_enroll_url, learning_path):
        """Test bulk enrollment updates existing enrollment allowed records."""
        email = "new_user@example.com"
        existing_allowed = LearningPathEnrollmentAllowed.objects.create(email=email, learning_path=learning_path)

        payload = {
            "learning_paths": learning_path.key,
            "emails": email,
            "reason": "TestReason",
        }
        response = staff_client.post(bulk_enroll_url, payload)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["enrollment_allowed_created"] == 0

        audit = existing_allowed.audit.get()
        assert audit.state_transition == LearningPathEnrollmentAudit.UNENROLLED_TO_ALLOWEDTOENROLL
        assert audit.reason == payload["reason"]

    def test_bulk_enrollment_with_invalid_learning_path(self, staff_client, bulk_enroll_url):
        """Test bulk enrollment with invalid learning path creates no enrollments."""
        payload = {
            "learning_paths": "invalid-path-key",
            "emails": "user1@example.com,user2@example.com",
        }
        response = staff_client.post(bulk_enroll_url, payload)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["enrollments_created"] == 0
        assert response.data["enrollment_allowed_created"] == 0

    def test_bulk_enrollment_with_invalid_and_valid_emails(self, staff_client, bulk_enroll_url, user, learning_path):
        """Test bulk enrollment with invalid email only creates enrollments for valid emails."""
        payload = {
            "learning_paths": learning_path.key,
            "emails": f"{user.email},invalid_email",
        }
        response = staff_client.post(bulk_enroll_url, payload)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["enrollments_created"] == 1
        assert response.data["enrollment_allowed_created"] == 0

        # Check learning path enrollment for valid user
        assert LearningPathEnrollment.objects.filter(user=user, learning_path=learning_path).exists()

        # Check enrollment allowed for invalid email doesn't exist
        assert not LearningPathEnrollmentAllowed.objects.filter(
            email="invalid_email", learning_path=learning_path
        ).exists()

    @pytest.mark.parametrize("http_method", ["post", "delete"])
    def test_bulk_operation_unauthenticated_and_non_staff(  # pylint: disable=too-many-positional-arguments
        self, api_client, bulk_enroll_url, user, learning_path, http_method
    ):
        """Test unauthenticated and non-staff users receive 403 for bulk operations (enroll/unenroll)."""
        payload = {
            "learning_paths": learning_path.key,
            "emails": user.email,
        }

        # Unauthenticated
        request_method_func = getattr(api_client, http_method)
        response = request_method_func(bulk_enroll_url, payload)
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Non-staff user
        api_client.force_authenticate(user=user)
        request_method_func = getattr(api_client, http_method)
        response = request_method_func(bulk_enroll_url, payload)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_bulk_enrollment_returned_counts_reflect_only_new_ones(  # pylint: disable=too-many-positional-arguments
        self, staff_client, staff_user, bulk_enroll_url, user, learning_path, active_enrollment
    ):
        """Test bulk enrollment counts only reflect new enrollments and creates ENROLLED_TO_ENROLLED audit."""
        payload = {
            "learning_paths": learning_path.key,
            "emails": user.email,
            "reason": "TestReason",
        }

        response = staff_client.post(bulk_enroll_url, payload)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["enrollments_created"] == 0
        assert response.data["enrollment_allowed_created"] == 0

        active_enrollment.refresh_from_db()
        assert active_enrollment.is_active is True

        latest_audit = active_enrollment.audit.last()
        assert latest_audit.state_transition == LearningPathEnrollmentAudit.ENROLLED_TO_ENROLLED
        assert latest_audit.enrolled_by == staff_user
        assert latest_audit.reason == payload["reason"]

    # pylint: disable=too-many-positional-arguments
    def test_re_enrollment(self, staff_client, staff_user, bulk_enroll_url, user, learning_path, inactive_enrollment):
        """Test bulk enrollment reactivates inactive enrollments and creates a correct audit."""
        payload = {
            "learning_paths": learning_path.key,
            "emails": user.email,
            "reason": "TestReason",
        }

        response = staff_client.post(bulk_enroll_url, payload)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["enrollments_created"] == 1

        inactive_enrollment.refresh_from_db()
        assert inactive_enrollment.is_active is True

        latest_audit = inactive_enrollment.audit.last()
        assert latest_audit.state_transition == LearningPathEnrollmentAudit.UNENROLLED_TO_ENROLLED
        assert latest_audit.enrolled_by == staff_user
        assert latest_audit.reason == payload["reason"]

    def test_bulk_enrollment_allowed_re_enrollment(self, staff_client, bulk_enroll_url, learning_path):
        """Test that bulk enrollment re-activates an inactive LearningPathEnrollmentAllowed."""
        email = "new_user@example.com"
        allowed = LearningPathEnrollmentAllowedFactory(email=email, learning_path=learning_path, is_active=False)
        payload = {"learning_paths": learning_path.key, "emails": email}

        response = staff_client.post(bulk_enroll_url, payload)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["enrollment_allowed_created"] == 1
        assert LearningPathEnrollmentAllowed.objects.count() == 1

        allowed.refresh_from_db()
        assert allowed.is_active

    # Bulk unenrollment tests

    def test_unenroll_success(self, staff_client, staff_user, bulk_enroll_url):
        """Test bulk unenrollment deactivates enrollments and enrollment allowed records and creates audit records."""
        user1 = UserFactory()
        user2 = UserFactory()
        user3 = UserFactory()  # Not enrolled, should not be affected.
        lp1 = LearningPathFactory()
        lp2 = LearningPathFactory()

        enrollments = [
            LearningPathEnrollmentFactory(user=user1, learning_path=lp1),
            LearningPathEnrollmentFactory(user=user1, learning_path=lp2),
            LearningPathEnrollmentFactory(user=user2, learning_path=lp1),
            LearningPathEnrollmentFactory(user=user2, learning_path=lp2, is_active=False),
        ]

        allowed_records = [
            LearningPathEnrollmentAllowedFactory(email="new_user@example.com", learning_path=lp1, is_active=True),
            LearningPathEnrollmentAllowedFactory(email="inactive@example.com", learning_path=lp2, is_active=False),
        ]

        payload = {
            "learning_paths": f"{lp1.key},{lp2.key}",
            "emails": f"{user1.email},{user2.email},{user3.email},new_user@example.com,inactive@example.com,invalid",
            "reason": "TestReason",
            "org": "TestOrg",
            "role": "TestRole",
        }

        response = staff_client.delete(bulk_enroll_url, payload)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert response.data["enrollments_unenrolled"] == 3
        assert response.data["enrollment_allowed_deactivated"] == 1

        # 4 enrollments + 3 unenrollments + 1 inactive update + 2 allowed records
        assert LearningPathEnrollmentAudit.objects.count() == 10

        for i, enrollment in enumerate(enrollments):
            enrollment.refresh_from_db()
            assert not enrollment.is_active

            audit = enrollment.audit.last()
            if i < 3:
                assert audit.state_transition == LearningPathEnrollmentAudit.ENROLLED_TO_UNENROLLED
            else:
                assert audit.state_transition == LearningPathEnrollmentAudit.UNENROLLED_TO_UNENROLLED
            assert audit.enrolled_by == staff_user
            assert audit.reason == payload["reason"]
            assert audit.org == payload["org"]
            assert audit.role == payload["role"]

        for i, allowed_record in enumerate(allowed_records):
            allowed_record.refresh_from_db()
            assert not allowed_record.is_active
            assert allowed_record.audit.count() == 1

            audit = allowed_record.audit.last()
            if i == 0:
                assert audit.state_transition == LearningPathEnrollmentAudit.ALLOWEDTOENROLL_TO_UNENROLLED
            else:
                assert audit.state_transition == LearningPathEnrollmentAudit.UNENROLLED_TO_UNENROLLED
            assert audit.enrolled_by == staff_user
            assert audit.reason == payload["reason"]
            assert audit.org == payload["org"]
            assert audit.role == payload["role"]

    def test_unenroll_with_invalid_learning_path(self, staff_client, bulk_enroll_url):
        """Test bulk unenrollment with invalid learning path creates no changes."""
        payload = {"learning_paths": "invalid-path-key", "emails": "user1@example.com"}
        response = staff_client.delete(bulk_enroll_url, payload)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert response.data["enrollments_unenrolled"] == 0

    def test_unenroll_empty_parameters(self, staff_client, bulk_enroll_url):
        """Test bulk unenrollment with empty or missing parameters doesn't affect existing enrollments."""
        response1 = staff_client.delete(bulk_enroll_url, {"learning_paths": "", "emails": ""})
        response2 = staff_client.delete(bulk_enroll_url, {})

        for response in [response1, response2]:
            assert response.status_code == status.HTTP_204_NO_CONTENT
            assert response.data["enrollments_unenrolled"] == 0


@pytest.mark.django_db
class TestLearningPathCourseEnrollment:

    @pytest.fixture
    def course_enrollment_url(self, learning_path_with_steps):
        return reverse(
            "learning-path-course-enroll",
            kwargs={
                "learning_path_key_str": str(learning_path_with_steps.key),
                "course_key_str": learning_path_with_steps.steps.first().course_key,
            },
        )

    @pytest.fixture
    def user_enrollment(self, user, learning_path_with_steps):
        return LearningPathEnrollmentFactory(user=user, learning_path=learning_path_with_steps, is_active=True)

    @patch("learning_paths.api.v1.views.enroll_user_in_course", return_value=True)
    def test_self_enrollment_successful(  # pylint: disable=too-many-positional-arguments
        self,
        mock_enroll,
        authenticated_client,
        user,
        course_enrollment_url,
        learning_path_with_steps,
        user_enrollment,
    ):
        """Test that a user can enroll themselves in a course that's part of a learning path they're enrolled in."""
        response = authenticated_client.post(course_enrollment_url)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["detail"] == "User successfully enrolled in the course."
        mock_enroll.assert_called_once_with(user, learning_path_with_steps.steps.first().course_key)

    def test_course_not_in_learning_path(self, authenticated_client, user, learning_path_with_steps, user_enrollment):
        """Test that a user cannot enroll in a course that's not part of the learning path."""
        url = reverse(
            "learning-path-course-enroll",
            kwargs={
                "learning_path_key_str": str(learning_path_with_steps.key),
                "course_key_str": "course-v1:edX+DemoX+NonExistent_Course",
            },
        )
        response = authenticated_client.post(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["detail"] == "The course is not part of this learning path."

    def test_user_not_enrolled_in_learning_path(
        self, authenticated_client, learning_path_with_steps, course_enrollment_url
    ):
        """Test that a user must be enrolled in the learning path to enroll in its courses."""
        response = authenticated_client.post(course_enrollment_url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["detail"] == "No LearningPath matches the given query."

    @patch("learning_paths.api.v1.views.enroll_user_in_course", return_value=False)
    def test_enrollment_failure(self, _mock_enroll, authenticated_client, course_enrollment_url, user_enrollment):
        """Test handling of enrollment failure."""
        response = authenticated_client.post(course_enrollment_url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["detail"] == "Failed to enroll the user in the course."

    def test_invite_only_learning_path_returns_404(self, authenticated_client, user, learning_path_with_invite_only):
        """Test that invite-only learning paths return 404 for non-enrolled users."""
        LearningPathStepFactory.create(
            learning_path=learning_path_with_invite_only,
            course_key="course-v1:edX+DemoX+Demo_Course",
        )

        url = reverse(
            "learning-path-course-enroll",
            kwargs={
                "learning_path_key_str": str(learning_path_with_invite_only.key),
                "course_key_str": learning_path_with_invite_only.steps.first().course_key,
            },
        )
        response = authenticated_client.post(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
