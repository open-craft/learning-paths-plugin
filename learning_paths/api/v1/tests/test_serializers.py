# pylint: disable=missing-module-docstring,missing-class-docstring
from unittest import TestCase

import pytest

from learning_paths.api.v1.serializers import (
    LearningPathAsProgramSerializer,
    LearningPathGradeSerializer,
    LearningPathProgressSerializer,
)
from learning_paths.models import LearningPath


@pytest.mark.django_db
class TestLearningPathAsProgramSerializer(TestCase):
    def test_data(self):
        """
        Tests LearningPathAsProgram serializer data.
        """
        learning_path = LearningPath.objects.create(
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
        self.assertDictEqual(serializer.data, expected)


@pytest.mark.django_db
class TestLearningPathProgressSerializer(TestCase):
    def test_data(self):
        """
        Tests LearningPathProgress serializer data.
        """
        learning_path = LearningPath.objects.create(
            uuid="817190bc-7bf1-4d95-aa43-bec5f58c2276",
            slug="learn-slug",
            display_name="My Test Learning Path",
            subtitle="Best path there is",
            image_url="https://image.go/toto.png",
            sequential=False,
        )
        progress_data = {
            "learning_path_id": learning_path.uuid,
            "progress": 0.25,
            "required_completion": 0.80,
        }
        progress_serializer = LearningPathProgressSerializer(progress_data)
        self.assertDictEqual(progress_serializer.data, progress_data)


@pytest.mark.django_db
class TestLearningPathGradeSerializer(TestCase):
    def test_data(self):
        """
        Tests LearningPathGrade serializer data.
        """
        learning_path = LearningPath.objects.create(
            uuid="817190bc-7bf1-4d95-aa43-bec5f58c2276",
            slug="learn-slug",
            display_name="My Test Learning Path",
            subtitle="Best path there is",
            image_url="https://image.go/toto.png",
            sequential=False,
        )
        grade_data = {
            "learning_path_id": learning_path.uuid,
            "grade": 0.25,
            "required_grade": 0.80,
        }
        grade_serializer = LearningPathGradeSerializer(grade_data)
        self.assertDictEqual(grade_serializer.data, grade_data)
