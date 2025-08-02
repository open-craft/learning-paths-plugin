"""
Serializer for LearningPath.
"""

from rest_framework import serializers

from learning_paths.models import (
    AcquiredSkill,
    LearningPath,
    LearningPathEnrollment,
    LearningPathStep,
    RequiredSkill,
    Skill,
)

DEFAULT_STATUS = "active"
IMAGE_WIDTH = 1440
IMAGE_HEIGHT = 480


class LearningPathAsProgramSerializer(serializers.ModelSerializer):
    """
    Serialize LearningPath as a Program to be ingested by course-discovery.

    Mocked data example:
    https://github.com/openedx/course-discovery/blob/d6a57fd69479b3d5f5afb682d2668b58503a6af6/course_discovery/apps/course_metadata/data_loaders/tests/mock_data.py#L580
    """

    name = serializers.CharField(source="display_name")
    marketing_slug = serializers.SerializerMethodField()
    title = serializers.CharField(source="display_name")
    status = serializers.SerializerMethodField()
    banner_image_urls = serializers.SerializerMethodField()
    organizations = serializers.SerializerMethodField()
    course_codes = serializers.SerializerMethodField()

    def get_marketing_slug(self, obj):
        return str(obj.key)

    def get_status(self, obj):  # pylint: disable=unused-argument
        return DEFAULT_STATUS

    def get_banner_image_urls(self, obj):
        if obj.image:
            image_key = f"w{IMAGE_WIDTH}h{IMAGE_HEIGHT}"
            return {image_key: obj.image.url}
        return {}

    def get_organizations(self, obj):  # pylint: disable=unused-argument
        return []

    def get_course_codes(self, obj):
        """returns course_codes as expected by course-discovery"""
        course_codes_dict = {}
        learning_path_course_keys = [course.course_key for course in obj.steps.all()]
        for course_key in learning_path_course_keys:
            run_mode = {"course_key": str(course_key), "run_key": course_key.run}
            if course_key.course in course_codes_dict:
                course_codes_dict[course_key.course]["run_modes"].append(run_mode)
            else:
                course_codes_dict[course_key.course] = {"run_modes": [run_mode]}

        return [{"key": key, **value} for key, value in course_codes_dict.items()]

    class Meta:
        model = LearningPath
        fields = (
            "uuid",
            "name",
            "marketing_slug",
            "title",
            "subtitle",
            "status",
            "banner_image_urls",
            "organizations",
            "course_codes",
        )


# pylint: disable=abstract-method
class LearningPathProgressSerializer(serializers.Serializer):
    learning_path_key = serializers.CharField()
    progress = serializers.FloatField()
    required_completion = serializers.FloatField()


class LearningPathGradeSerializer(serializers.Serializer):
    """
    Serializer for learning path grade.
    """

    learning_path_key = serializers.CharField()
    grade = serializers.FloatField()
    required_grade = serializers.FloatField()


class LearningPathStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningPathStep
        fields = ["order", "course_key", "course_dates", "weight"]


class LearningPathListSerializer(serializers.ModelSerializer):
    """Serializer for the learning path list."""

    steps = LearningPathStepSerializer(many=True, read_only=True)
    required_completion = serializers.FloatField(source="grading_criteria.required_completion", read_only=True)
    enrollment_date = serializers.SerializerMethodField()
    invite_only = serializers.BooleanField()
    image = serializers.ImageField(read_only=True)

    class Meta:
        model = LearningPath
        fields = [
            "key",
            "display_name",
            "image",
            "sequential",
            "steps",
            "required_completion",
            "enrollment_date",
            "invite_only",
        ]

    def get_enrollment_date(self, obj):
        """
        Check if the current user is enrolled in this learning path.
        """
        if hasattr(obj, "enrollment_date"):
            return obj.enrollment_date
        return None


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ["id", "display_name"]


class RequiredSkillSerializer(serializers.ModelSerializer):
    """
    Serializer for required skill.
    """

    skill = SkillSerializer()

    class Meta:
        model = RequiredSkill
        fields = ["skill", "level"]


class AcquiredSkillSerializer(serializers.ModelSerializer):
    """
    Serializer for acquired skill.
    """

    skill = SkillSerializer()

    class Meta:
        model = AcquiredSkill
        fields = ["skill", "level"]


class LearningPathDetailSerializer(LearningPathListSerializer):
    """
    Serializer for learning path details.
    """

    required_skills = RequiredSkillSerializer(source="requiredskill_set", many=True, read_only=True)
    acquired_skills = AcquiredSkillSerializer(source="acquiredskill_set", many=True, read_only=True)

    class Meta(LearningPathListSerializer.Meta):
        fields = LearningPathListSerializer.Meta.fields + [
            "subtitle",
            "description",
            "level",
            "duration",
            "time_commitment",
            "required_skills",
            "acquired_skills",
        ]


class LearningPathEnrollmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningPathEnrollment
        fields = ("user", "learning_path", "is_active", "created")
