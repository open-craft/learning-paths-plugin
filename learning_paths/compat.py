"""
Compatibility layer for testing without Open edX.
"""

from unittest.mock import Mock

from django.contrib.auth.models import AbstractBaseUser
from opaque_keys.edx.keys import CourseKey

try:
    from openedx.core.djangoapps.content.learning_sequences.api import (
        get_course_keys_with_outlines,
    )
except ImportError:
    get_course_keys_with_outlines = Mock()

try:
    from lms.djangoapps.grades.course_grade_factory import CourseGradeFactory
except ImportError:
    CourseGradeFactory = Mock()

try:
    from openedx.core.djangoapps.catalog.utils import get_catalog_api_client
except ImportError:
    get_catalog_api_client = Mock()


def get_user_course_grade(user: AbstractBaseUser, course_key: CourseKey):
    """
    Retrieve the CourseGrade object for a user in a specific course.
    """
    course_grade = CourseGradeFactory().read(user, course_key=course_key)
    return course_grade


__all__ = [
    "get_course_keys_with_outlines",
    "get_catalog_api_client",
    "get_user_course_grade",
]
