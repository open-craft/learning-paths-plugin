"""Pytest fixtures."""

import pytest
from django.test import override_settings


@pytest.fixture
def temp_media(tmpdir):
    """Temporarily override MEDIA_ROOT to a pytest tmpdir."""
    temp_dir = str(tmpdir.mkdir("media"))

    with override_settings(MEDIA_ROOT=temp_dir):
        yield temp_dir
