"""
Keys and fields used by learning-paths-plugin.
"""

import re
from typing import Self

from django.core.exceptions import ValidationError
from opaque_keys import InvalidKeyError
from opaque_keys.edx.django.models import LearningContextKeyField
from opaque_keys.edx.keys import LearningContextKey

COURSE_KEY_NAMESPACE = "course-v1"
COURSE_KEY_PATTERN = r"([^+]+)\+([^+]+)\+([^+]+)"
COURSE_KEY_URL_PATTERN = rf"(?P<course_key_str>{COURSE_KEY_NAMESPACE}:{COURSE_KEY_PATTERN})"

LEARNING_PATH_NAMESPACE = "path-v1"
LEARNING_PATH_PATTERN = r"([^+]+)\+([^+]+)\+([^+]+)\+([^+]+)"
LEARNING_PATH_URL_PATTERN = rf"(?P<learning_path_key_str>{LEARNING_PATH_NAMESPACE}:{LEARNING_PATH_PATTERN})"


class LearningPathKey(LearningContextKey):
    """
    A key for a learning path.

    Format: path-v1:{name}+{number}+{run}+{group}
    """

    CANONICAL_NAMESPACE = LEARNING_PATH_NAMESPACE
    KEY_FIELDS = ("org", "number", "run", "group")
    CHECKED_INIT = False

    __slots__ = KEY_FIELDS

    _learning_path_key_regex = re.compile(rf"^{LEARNING_PATH_PATTERN}$")

    def __init__(self, org, number, run, group):
        """Initialize a LearningPathKey instance."""
        super().__init__(org=org, number=number, run=run, group=group)

    @classmethod
    def _from_string(cls, serialized: str) -> Self:
        """Return an instance of this class constructed from the given string."""
        match = cls._learning_path_key_regex.match(serialized)
        if not match:
            raise InvalidKeyError(cls, serialized)
        return cls(*match.groups())

    def _to_string(self) -> str:
        """Return a string representing this key."""
        return "+".join([self.org, self.number, self.run, self.group])  # pylint: disable=no-member


class LearningPathKeyField(LearningContextKeyField):
    """Field for storing LearningPathKey objects."""

    description = "A LearningPathKey object"
    KEY_CLASS = LearningPathKey
    # Declare the field types for the django-stubs mypy type hint plugin:
    _pyi_private_set_type: LearningPathKey | str | None
    _pyi_private_get_type: LearningPathKey | None

    def to_python(self, value):
        """Convert the input value to a LearningPathKey object."""
        try:
            return super().to_python(value)
        except InvalidKeyError:
            raise ValidationError(  # pylint: disable=raise-missing-from
                "Invalid format. Use: 'path-v1:{org}+{number}+{run}+{group}'"
            )
