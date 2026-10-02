# pylint: disable=redefined-outer-name,unused-argument,protected-access
"""
Tests for the learning_paths models.
"""

import re
from datetime import datetime, timezone

import pytest
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.paginator import Paginator
from django.db import IntegrityError
from slugify import slugify

from learning_paths.keys import LearningPathKey
from learning_paths.models import (
    LearningPath,
    LearningPathEnrollment,
    LearningPathEnrollmentAllowed,
    LearningPathEnrollmentAudit,
)

from .factories import (
    LearningPathEnrollmentAllowedFactory,
    LearningPathEnrollmentAuditFactory,
    LearningPathFactory,
)


@pytest.fixture
def learning_path_key():
    """Create a learning path key for testing."""
    return LearningPathKey("org", "number", "run", "group")


@pytest.fixture
def learning_path(learning_path_key):
    """Create a basic learning path for tests."""
    return LearningPath.objects.create(
        key=learning_path_key,
        display_name="Test Learning Path",
        subtitle="Test Subtitle",
        description="Test description",
        level="intermediate",
        duration="30 days",
        time_commitment="4-6 hours/week",
        sequential=True,
    )


@pytest.fixture
def test_image(temp_media):
    """Create an image for testing."""
    return SimpleUploadedFile(name="test_image.png", content=b"test image content", content_type="image/png")


@pytest.mark.django_db
class TestLearningPath:
    """Tests for the LearningPath model."""

    def test_creation(self, learning_path):
        """Test creating a learning path."""
        assert learning_path.display_name == "Test Learning Path"
        assert learning_path.sequential is True

    def test_string_representation(self, learning_path):
        """Test the string representation."""
        assert str(learning_path) == str(learning_path.key)

    def test_uuid_auto_generation(self, learning_path_key):
        """Test that the UUID is auto-generated."""
        path = LearningPath.objects.create(key=learning_path_key)
        assert path.uuid is not None

    def test_create_with_image(self, learning_path_key, test_image):
        """Test creating a learning path with an image."""
        path = LearningPath.objects.create(
            key=learning_path_key,
            display_name="Test create with image",
            image=test_image,
        )
        assert path.image is not None
        assert slugify(str(path.key)) in path.image.name
        assert ".png" in path.image.name

    def test_image_replacement(self, learning_path, test_image):
        """Test that old images are deleted when replaced."""
        learning_path.image = test_image
        learning_path.save()
        original_image = learning_path.image
        assert default_storage.exists(original_image.name)

        new_image = SimpleUploadedFile(name="new_image.png", content=b"new image content", content_type="image/png")
        learning_path.image = new_image
        learning_path.save()

        assert learning_path.image is not None
        assert learning_path.image.path != original_image.path
        assert default_storage.exists(learning_path.image.name)
        assert not default_storage.exists(original_image.name)

    def test_image_deletion_on_delete(self, learning_path_key, test_image):
        """Test that images are deleted when the learning path is deleted."""
        path = LearningPath.objects.create(
            key=learning_path_key,
            display_name="Test image deletion",
            image=test_image,
        )

        image_path = path.image.name
        assert default_storage.exists(image_path)

        path.delete()
        assert not default_storage.exists(image_path)

    def test_upload_path_includes_random_suffix(self, learning_path):
        """Test that the upload path includes a random suffix."""
        path1 = learning_path._learning_path_image_upload_path("test.jpg")
        path2 = learning_path._learning_path_image_upload_path("test.jpg")

        slugified_key = slugify(str(learning_path.key))
        regexp = rf"learning_paths/images/{slugified_key}_.*\.jpg"

        assert re.search(regexp, path1)
        assert re.search(regexp, path2)
        assert path1 != path2

    def test_key_required(self, learning_path_key):
        """Test that the key is required."""
        with pytest.raises(ValidationError) as exc:
            LearningPath.objects.create()
        assert exc.value.message == "Learning Path key cannot be empty."

    def test_unique_key(self, learning_path, learning_path_key):
        """Test that key must be unique."""
        with pytest.raises(
            IntegrityError,
            match="UNIQUE constraint failed: learning_paths_learningpath.key",
        ):
            LearningPath.objects.create(key=learning_path_key)

    def test_grading_criteria_auto_creation(self, learning_path):
        """Test that grading criteria is automatically created with a learning path."""

        criteria = learning_path.grading_criteria
        assert criteria is not None
        assert criteria.required_completion == 0.80
        assert criteria.required_grade == 0.75


@pytest.mark.django_db
class TestLearningPathEnrollmentAllowed:
    """Tests for the LearningPathEnrollmentAllowed model."""

    @pytest.mark.parametrize("user_provided", [True, False])
    def test_string_representation(self, user, learning_path, user_provided):
        """Test the string representation."""
        user_kwarg = {"user": user} if user_provided else {}
        allowed = LearningPathEnrollmentAllowedFactory(email=user.email, learning_path=learning_path, **user_kwarg)
        expected_str = f"LearningPathEnrollmentAllowed for {user.email} in {learning_path.key}"
        assert str(allowed) == expected_str

    def test_is_active_defaults_to_true(self, learning_path):
        """Test that is_active field defaults to True."""
        allowed = LearningPathEnrollmentAllowed(email="test@example.com", learning_path=learning_path)
        assert allowed.is_active is True


@pytest.mark.django_db
class TestLearningPathEnrollmentAudit:
    """Tests for the LearningPathEnrollmentAudit model."""

    def test_string_representation_with_enrollment(self, user, learning_path, active_enrollment):
        """Test the string representation when linked to a LearningPathEnrollment."""
        audit = active_enrollment.audit.get()
        expected_str = (
            f"{LearningPathEnrollmentAudit.UNENROLLED_TO_ENROLLED} for {user.username} in {learning_path.key}"
        )
        assert str(audit) == expected_str

    def test_string_representation_with_enrollment_allowed_and_user(self, user, learning_path):
        """Test the string representation when linked to LearningPathEnrollmentAllowed with a user."""
        enrollment_allowed = LearningPathEnrollmentAllowedFactory(
            user=user, email=user.email, learning_path=learning_path
        )
        enrollment_allowed._audit = {"reason": "TestReason"}
        enrollment_allowed.save()
        audit = enrollment_allowed.audit.get()
        expected_str = (
            f"{LearningPathEnrollmentAudit.UNENROLLED_TO_ALLOWEDTOENROLL} for {user.username} in {learning_path.key}"
        )
        assert str(audit) == expected_str

    def test_string_representation_with_enrollment_allowed_no_user(self, learning_path):
        """Test the string representation when linked to LearningPathEnrollmentAllowed without a user (email only)."""
        email = "new_user@example.com"
        enrollment_allowed = LearningPathEnrollmentAllowedFactory(email=email, learning_path=learning_path)
        enrollment_allowed._audit = {"reason": "TestReason"}
        enrollment_allowed.save()
        audit = enrollment_allowed.audit.get()
        expected_str = f"{LearningPathEnrollmentAudit.UNENROLLED_TO_ALLOWEDTOENROLL} for {email} in {learning_path.key}"
        assert str(audit) == expected_str

    def test_string_representation_no_enrollment_or_allowed(self):
        """Test the string representation when no enrollment or enrollment_allowed is linked."""
        audit = LearningPathEnrollmentAuditFactory()
        expected_str = f"{LearningPathEnrollmentAudit.DEFAULT_TRANSITION_STATE} for unknown in unknown"
        assert str(audit) == expected_str


@pytest.mark.django_db
@pytest.mark.parametrize("staff", [True, False])
def test_visible_paths_use_unique_id_to_break_equal_enrollment_dates(user, staff):
    """NULL and equal dates need a total ordering across successive pages."""
    user.is_staff = staff
    user.save()
    # Deliberately opposite lexical names: the tie-breaker is immutable ID,
    # rather than editable display text or key spelling.
    paths = [LearningPathFactory(invite_only=False, display_name=name)
             for name in ("Zulu", "Alpha", "Yankee", "Beta")]
    same_date = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for path in paths[:2]:
        enrollment = LearningPathEnrollment.objects.create(learning_path=path, user=user, is_active=True)
        LearningPathEnrollment.objects.filter(pk=enrollment.pk).update(created=same_date)
    hidden = LearningPathFactory(invite_only=True)
    visible = LearningPath.objects.get_paths_visible_to_user(user)
    # SQLite may coincidentally return ID order without the tie-breaker. Require
    # the unique term in the actual ORM ordering so that control cannot pass
    # just because this small fixture happened to use one database plan.
    assert visible.query.order_by[-1] == "id"
    expected = [path.id for path in paths] + ([hidden.id] if staff else [])
    assert list(visible.values_list("id", flat=True)) == expected
    pages = Paginator(visible, 2)
    observed = [path.id for number in pages.page_range for path in pages.page(number)]
    assert observed == expected
    assert len(observed) == len(set(observed))
