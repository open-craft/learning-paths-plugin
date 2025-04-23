# pylint: disable=missing-module-docstring
import pytest

from learning_paths.api.v1.serializers import (
    LearningPathAsProgramSerializer,
    LearningPathDetailSerializer,
    LearningPathGradeSerializer,
    LearningPathListSerializer,
    LearningPathProgressSerializer,
)
from learning_paths.tests.factories import (
    LearningPathEnrollmentFactory,
    LearningPathFactory,
    UserFactory,
)


@pytest.mark.django_db
def test_learning_path_as_program_serializer():
    """
    Tests LearningPathAsProgram serializer data.
    """
    learning_path = LearningPathFactory(
        uuid="817190bc-7bf1-4d95-aa43-bec5f58c2276",
        display_name="My Test Learning Path",
        subtitle="Best path there is",
        image_url="https://image.go/toto.png",
        sequential=False,
    )
    serializer = LearningPathAsProgramSerializer(learning_path)
    expected = {
        "uuid": "817190bc-7bf1-4d95-aa43-bec5f58c2276",
        "name": "My Test Learning Path",
        "marketing_slug": str(learning_path.key),
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


@pytest.mark.django_db
def test_list_serializer():
    """
    Test the default values of the LearningPathListSerializer.
    """
    learning_path = LearningPathFactory()
    serializer = LearningPathListSerializer(learning_path)
    expected = {
        "key": str(learning_path.key),
        "display_name": learning_path.display_name,
        "image_url": "",
        "invite_only": True,
        "sequential": False,
        "steps": [],
        "required_completion": 0.8,
        "is_enrolled": False,
    }
    assert dict(serializer.data) == expected


@pytest.mark.django_db
@pytest.mark.parametrize("is_enrolled", [True, False], ids=["enrolled", "not_enrolled"])
def test_list_serializer_enrollment(is_enrolled):
    """
    Tests LearningPathListSerializer shows is_enrolled as True when a user is enrolled.
    """
    user = UserFactory()
    learning_path = LearningPathFactory(invite_only=False)
    LearningPathEnrollmentFactory(
        user=user, learning_path=learning_path, is_active=is_enrolled
    )

    # Get the annotated learning path with the enrollment status.
    learning_path = learning_path.__class__.objects.get_paths_visible_to_user(user).get(
        key=learning_path.key
    )

    serializer = LearningPathListSerializer(learning_path)
    assert serializer.data["is_enrolled"] is is_enrolled


@pytest.mark.django_db
def test_detail_serializer():
    """
    Tests LearningPathDetailSerializer default values.
    """
    learning_path = LearningPathFactory()
    expected = {
        "key": str(learning_path.key),
        "display_name": learning_path.display_name,
        "subtitle": "",
        "description": learning_path.description,
        "image_url": "",
        "invite_only": True,
        "level": "",
        "sequential": False,
        "duration_in_days": None,
        "required_skills": [],
        "acquired_skills": [],
        "steps": [],
        "is_enrolled": False,
        "required_completion": 0.8,
    }
    serializer = LearningPathDetailSerializer(learning_path)
    assert dict(serializer.data) == expected
