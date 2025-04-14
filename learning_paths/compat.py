"""
Compatibility layer for testing without Open edX.
"""

from datetime import datetime

from django.contrib.auth.models import AbstractBaseUser
from opaque_keys.edx.keys import CourseKey


def get_user_course_grade(user: AbstractBaseUser, course_key: CourseKey):
    """
    Retrieve the CourseGrade object for a user in a specific course.
    """
    # pylint: disable=import-outside-toplevel, import-error
    from lms.djangoapps.grades.course_grade_factory import CourseGradeFactory

    course_grade = CourseGradeFactory().read(user, course_key=course_key)
    return course_grade


def get_catalog_api_client(user: AbstractBaseUser):
    """
    Retrieve the api client for user.
    """
    # pylint: disable=import-outside-toplevel, import-error
    from openedx.core.djangoapps.catalog.utils import (
        get_catalog_api_client as api_client,
    )

    return api_client(user)


def get_course_keys_with_outlines():
    """
    Retrieve course keys.
    """
    # pylint: disable=import-outside-toplevel, import-error
    from openedx.core.djangoapps.content.learning_sequences.api import (
        get_course_keys_with_outlines as course_keys_with_outlines,
    )

    return course_keys_with_outlines()


def get_course_due_date(course_key: CourseKey) -> datetime | None:
    """
    Retrieve course end date.
    """
    # pylint: disable=import-outside-toplevel, import-error
    from openedx.core.djangoapps.content.course_overviews.models import CourseOverview

    try:
        overview = CourseOverview.objects.get(id=course_key)
        return overview.end
    except CourseOverview.DoesNotExist:
        return None


__all__ = [
    "get_course_keys_with_outlines",
    "get_catalog_api_client",
    "get_user_course_grade",
    "get_course_due_date",
]
