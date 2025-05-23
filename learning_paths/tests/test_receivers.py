# pylint: disable=redefined-outer-name
"""Tests for the signals module."""

import pytest
from django.contrib.auth import get_user_model

from learning_paths.models import LearningPathEnrollment, LearningPathEnrollmentAllowed
from learning_paths.receivers import process_pending_enrollments

from .factories import (
    LearningPathEnrollmentAllowedFactory,
    LearningPathFactory,
    UserFactory,
)

User = get_user_model()


@pytest.fixture
def user_email():
    """Return a test email address."""
    return "test@example.com"


@pytest.fixture
def learning_paths():
    """Create two learning paths for testing."""
    return [LearningPathFactory(), LearningPathFactory()]


@pytest.mark.django_db
def test_process_pending_enrollments_with_pending_enrollments(user_email, learning_paths):
    """
    GIVEN that there are LearningPathEnrollmentAllowed objects for an email
    WHEN the process_pending_enrollments signal handler is triggered
    THEN actual enrollment objects are created for the user
    """
    pending_entry_1 = LearningPathEnrollmentAllowedFactory(email=user_email, learning_path=learning_paths[0])
    pending_entry_2 = LearningPathEnrollmentAllowedFactory(email=user_email, learning_path=learning_paths[1])

    user = UserFactory(email=user_email)
    process_pending_enrollments(sender=User, instance=user, created=True)

    pending_entry_1.refresh_from_db()
    pending_entry_2.refresh_from_db()
    assert pending_entry_1.user == user
    assert pending_entry_2.user == user

    enrollments = LearningPathEnrollment.objects.all()
    assert len(enrollments) == 2
    assert all(e.user == user for e in enrollments)
    assert enrollments[0].learning_path == pending_entry_1.learning_path
    assert enrollments[1].learning_path == pending_entry_2.learning_path


@pytest.mark.django_db
def test_process_pending_enrollments_when_no_pending_enrollments(user_email):
    """
    GIVEN that there are no LearningPathEnrollmentAllowed objects for an email
    WHEN the process_pending_enrollments signal handler is triggered
    THEN no LearningPathEnrollment objects are created
    """
    user = UserFactory(email=user_email)
    process_pending_enrollments(sender=User, instance=user, created=True)

    enrollments = LearningPathEnrollment.objects.all()
    assert len(enrollments) == 0


@pytest.mark.django_db
def test_process_pending_enrollments_when_not_created(user_email):
    """
    GIVEN that a user is updated
    WHEN the process_pending_enrollments signal handler is triggered with created=False
    THEN no enrollment objects are created
    """
    user = UserFactory(email=user_email)

    # Trigger the signal manually with created=False (user update)
    process_pending_enrollments(sender=User, instance=user, created=False)

    pending_entries = LearningPathEnrollmentAllowed.objects.all()
    assert len(pending_entries) == 0

    enrollments = LearningPathEnrollment.objects.all()
    assert len(enrollments) == 0
