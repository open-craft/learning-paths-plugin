# pylint: disable=missing-module-docstring
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

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
)


@pytest.mark.django_db
def test_learning_path_as_program_serializer(
    temp_media,
):  # pylint: disable=unused-argument
    """
    Tests LearningPathAsProgram serializer data.
    """
    test_image = SimpleUploadedFile(name="test_image.png", content=b"test image content", content_type="image/png")

    learning_path = LearningPathFactory(
        uuid="817190bc-7bf1-4d95-aa43-bec5f58c2276",
        display_name="My Test Learning Path",
        subtitle="Best path there is",
        image=test_image,
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
        "banner_image_urls": {"w1440h480": learning_path.image.url},
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
        "image": None,
        "invite_only": True,
        "sequential": False,
        "steps": [],
        "required_completion": 0.8,
        "enrollment_date": None,
    }
    assert dict(serializer.data) == expected


@pytest.mark.django_db
@pytest.mark.parametrize("is_enrolled", [True, False], ids=["enrolled", "not_enrolled"])
def test_list_serializer_enrollment(user, learning_path, is_enrolled):
    """
    Tests LearningPathListSerializer shows enrollment_date when a user is enrolled.
    """
    enrollment = LearningPathEnrollmentFactory(user=user, learning_path=learning_path, is_active=is_enrolled)

    # Get the annotated learning path with the enrollment status.
    learning_path = learning_path.__class__.objects.get_paths_visible_to_user(user).get(key=learning_path.key)

    serializer = LearningPathListSerializer(learning_path)
    assert serializer.data["enrollment_date"] == (enrollment.created if is_enrolled else None)


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
        "image": None,
        "invite_only": True,
        "level": "",
        "sequential": False,
        "duration": "",
        "time_commitment": "",
        "required_skills": [],
        "acquired_skills": [],
        "steps": [],
        "enrollment_date": None,
        "required_completion": 0.8,
    }
    serializer = LearningPathDetailSerializer(learning_path)
    assert dict(serializer.data) == expected
