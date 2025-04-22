# pylint: disable=missing-module-docstring
import pytest

from learning_paths.api.v1.serializers import (
    LearningPathAsProgramSerializer,
    LearningPathGradeSerializer,
    LearningPathProgressSerializer,
)
from learning_paths.api.v1.tests.factories import LearningPathFactory


@pytest.mark.django_db
def test_learning_path_as_program_serializer():
    """
    Tests LearningPathAsProgram serializer data.
    """
    learning_path = LearningPathFactory(
        uuid="817190bc-7bf1-4d95-aa43-bec5f58c2276",
        slug="learn-slug",
        display_name="My Test Learning Path",
        subtitle="Best path there is",
        image_url="https://image.go/toto.png",
        sequential=False,
    )
    serializer = LearningPathAsProgramSerializer(learning_path)
    expected = {
        "uuid": "817190bc-7bf1-4d95-aa43-bec5f58c2276",
        "name": "My Test Learning Path",
        "marketing_slug": "learn-slug",
        "title": "My Test Learning Path",
        "subtitle": "Best path there is",
        "status": "active",
        "banner_image_urls": {"w1440h480": "https://image.go/toto.png"},
        "organizations": [],
        "course_codes": [],
    }
    assert dict(serializer.data) == expected


@pytest.mark.django_db
def test_learning_path_progress_serializer():
    """
    Tests LearningPathProgress serializer data.
    """
    learning_path = LearningPathFactory(
        key="path-v1:test+test+test+test",
        uuid="817190bc-7bf1-4d95-aa43-bec5f58c2276",
        slug="learn-slug",
        display_name="My Test Learning Path",
        subtitle="Best path there is",
        image_url="https://image.go/toto.png",
        sequential=False,
    )
    progress_data = {
        "learning_path_key": str(learning_path.key),
        "progress": 0.25,
        "required_completion": 0.80,
    }
    progress_serializer = LearningPathProgressSerializer(progress_data)
    assert dict(progress_serializer.data) == progress_data


@pytest.mark.django_db
def test_learning_path_grade_serializer():
    """
    Tests LearningPathGrade serializer data.
    """
    learning_path = LearningPathFactory(
        key="path-v1:OpenedX+DemoX+DemoRun+DemoGroup",
        uuid="817190bc-7bf1-4d95-aa43-bec5f58c2276",
        slug="learn-slug",
        display_name="My Test Learning Path",
        subtitle="Best path there is",
        image_url="https://image.go/toto.png",
        sequential=False,
    )
    grade_data = {
        "learning_path_key": str(learning_path.key),
        "grade": 0.25,
        "required_grade": 0.80,
    }
    grade_serializer = LearningPathGradeSerializer(grade_data)
    assert dict(grade_serializer.data) == grade_data
