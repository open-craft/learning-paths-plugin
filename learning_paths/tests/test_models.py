# pylint: disable=redefined-outer-name,unused-argument,protected-access
"""
Tests for the learning_paths models.
"""

import re

import pytest
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from slugify import slugify

from learning_paths.keys import LearningPathKey
from learning_paths.models import LearningPath


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
        duration_in_days=30,
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
