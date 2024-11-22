"""
Compatibility layer for testing without Open edX.
"""

from unittest.mock import Mock

try:
    from openedx.core.djangoapps.content.learning_sequences.api import (
        get_course_keys_with_outlines,
    )
except ImportError:
    get_course_keys_with_outlines = Mock()
try:
    from common.djangoapps.student.models import CourseEnrollment
except ImportError:
    CourseEnrollment = Mock()

__all__ = ["get_course_keys_with_outlines", "CourseEnrollment"]
