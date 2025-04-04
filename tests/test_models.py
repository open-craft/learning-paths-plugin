"""
Tests for the learning_paths models.
"""

# pylint: disable=redefined-outer-name,unused-argument

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

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
        slug="test-path",
        display_name="Test Learning Path",
        subtitle="Test Subtitle",
        description="Test description",
        level="intermediate",
        duration_in_days=30,
        sequential=True,
    )


@pytest.mark.django_db
class TestLearningPath:
    """Tests for the LearningPath model."""

    def test_creation(self, learning_path):
        """Test creating a learning path."""
        assert learning_path.display_name == "Test Learning Path"
        assert learning_path.slug == "test-path"
        assert learning_path.sequential is True

    def test_string_representation(self, learning_path):
        """Test the string representation."""
        assert str(learning_path) == "Test Learning Path"

    def test_uuid_auto_generation(self, learning_path_key):
        """Test that the UUID is auto-generated."""
        path = LearningPath.objects.create(key=learning_path_key)
        assert path.uuid is not None

    # TODO: https://github.com/open-craft/learning-paths-plugin/issues/12
    @pytest.mark.skip(reason="UUID migration incomplete")
    def test_key_required(self, learning_path_key):
        """Test that key is required."""
        with pytest.raises(ValidationError):
            LearningPath.objects.create()

    def test_unique_key(self, learning_path, learning_path_key):
        """Test that key must be unique."""
        with pytest.raises(
            IntegrityError,
            match="UNIQUE constraint failed: learning_paths_learningpath.key",
        ):
            LearningPath.objects.create(key=learning_path_key)

    def test_unique_slug(self, learning_path, learning_path_key):
        """Test that slug must be unique."""
        with pytest.raises(
            IntegrityError,
            match="UNIQUE constraint failed: learning_paths_learningpath.slug",
        ):
            LearningPath.objects.create(
                key=LearningPathKey("org2", "number2", "run2", "group2"),
                slug=learning_path.slug,
            )

    def test_grading_criteria_auto_creation(self, learning_path):
        """Test that grading criteria is automatically created with a learning path."""

        criteria = learning_path.grading_criteria
        assert criteria is not None
        assert criteria.required_completion == 0.80
        assert criteria.required_grade == 0.75
