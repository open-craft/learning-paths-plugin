"""
Tests for the learning-paths-plugin keys module.
"""

import pytest
from django.core.exceptions import ValidationError
from opaque_keys import InvalidKeyError

from learning_paths.keys import LearningPathKey, LearningPathKeyField


class TestLearningPathKey:
    """Tests for LearningPathKey class."""

    # pylint: disable=no-member
    def test_create_key(self):
        """Test creation of a valid key."""
        key = LearningPathKey("org", "number", "run", "group")
        assert key.org == "org"
        assert key.number == "number"
        assert key.run == "run"
        assert key.group == "group"
        assert key.CANONICAL_NAMESPACE == "path-v1"

    def test_key_from_string(self):
        """Test creating a key from a string."""
        key_str = "path-v1:org+number+run+group"
        assert LearningPathKey.from_string(key_str) == LearningPathKey(
            "org", "number", "run", "group"
        )

    def test_key_to_string(self):
        """Test serializing a key to a string."""
        key = LearningPathKey("org", "number", "run", "group")
        assert str(key) == "path-v1:org+number+run+group"

    @pytest.mark.parametrize(
        "key_str",
        [
            "path-v1:invalid_key_format",
            "path-v1:org+number+run+group+extra",  # Extra part
            "path-v1:org+number+run",  # Missing group
            "number+run+group",  # Missing namespace
        ],
    )
    def test_invalid_key_string(self, key_str):
        """Test that an invalid key string raises an error."""
        with pytest.raises(InvalidKeyError):
            LearningPathKey.from_string(key_str)

    def test_key_equality(self):
        """Test that equal keys compare as equal."""
        key1 = LearningPathKey("org", "number", "run", "group")
        key2 = LearningPathKey("org", "number", "run", "group")
        key3 = LearningPathKey("org", "different", "run", "group")

        assert key1 == key2
        assert key1 != key3


class TestLearningPathKeyField:
    """Tests for LearningPathKeyField class."""

    def test_to_python_with_none(self):
        """Test that None is returned for empty values."""
        field = LearningPathKeyField()
        assert field.to_python(None) is None
        assert field.to_python("") is None

    def test_to_python_with_key_object(self):
        """Test that a key object is returned as-is."""
        field = LearningPathKeyField()
        key = LearningPathKey("org", "number", "run", "group")
        assert field.to_python(key) is key

    def test_to_python_with_valid_string(self):
        """Test conversion of a valid string to a key."""
        field = LearningPathKeyField()
        key_str = "path-v1:org+number+run+group"
        key = field.to_python(key_str)

        assert isinstance(key, LearningPathKey)
        assert key == LearningPathKey.from_string(key_str)

    @pytest.mark.parametrize(
        "key_str",
        [
            "path-v1:invalid_key_format",
            "path-v1:org+number+run+group+extra",  # Extra part
            "path-v1:org+number+run",  # Missing group
            "number+run+group",  # Missing namespace
        ],
    )
    def test_to_python_with_invalid_string(self, key_str):
        """Test that an invalid string raises a ValidationError."""
        field = LearningPathKeyField()

        with pytest.raises(ValidationError):
            field.to_python(key_str)

    def test_to_python_validation_error_message(self):
        """Test that the validation error message is as expected."""
        field = LearningPathKeyField()

        with pytest.raises(ValidationError) as excinfo:
            field.to_python("invalid_key_format")

        assert "Invalid format. Use: 'path-v1:{org}+{number}+{run}+{group}'" in str(
            excinfo.value
        )
