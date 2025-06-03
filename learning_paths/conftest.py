"""Pytest fixtures."""

# pylint: disable=redefined-outer-name

import pytest
from django.test import override_settings

from learning_paths.tests.factories import (
    LearningPathEnrollmentFactory,
    LearningPathFactory,
    UserFactory,
)


@pytest.fixture
def user():
    """Create a single user for testing."""
    return UserFactory()


@pytest.fixture
def learning_path():
    """Create a single learning path for testing."""
    return LearningPathFactory(invite_only=False)


@pytest.fixture
def learning_path_with_invite_only():
    """Create a learning path that is invite-only."""
    return LearningPathFactory()


@pytest.fixture
def active_enrollment(user, learning_path):
    """Create an active enrollment for the user in the learning path."""
    return LearningPathEnrollmentFactory(user=user, learning_path=learning_path, is_active=True)


@pytest.fixture
def inactive_enrollment(user, learning_path):
    """Create an inactive enrollment for the user in the learning path."""
    return LearningPathEnrollmentFactory(user=user, learning_path=learning_path, is_active=False)


@pytest.fixture
def temp_media(tmpdir):
    """Temporarily override MEDIA_ROOT to a pytest tmpdir."""
    temp_dir = str(tmpdir.mkdir("media"))

    with override_settings(MEDIA_ROOT=temp_dir):
        yield temp_dir
