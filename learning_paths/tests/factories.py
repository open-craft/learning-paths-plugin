# pylint: disable=missing-module-docstring,missing-class-docstring
from datetime import datetime, timezone

import factory
from django.contrib import auth
from factory.fuzzy import FuzzyText

from learning_paths.keys import LearningPathKey
from learning_paths.models import (
    AcquiredSkill,
    LearningPath,
    LearningPathEnrollment,
    LearningPathEnrollmentAllowed,
    LearningPathGradingCriteria,
    LearningPathStep,
    RequiredSkill,
    Skill,
)

User = auth.get_user_model()

USER_PASSWORD = "password"


class UserFactory(factory.django.DjangoModelFactory):
    username = factory.Sequence(lambda n: "user_%d" % n)
    password = factory.PostGenerationMethodCall("set_password", USER_PASSWORD)
    is_active = True
    is_superuser = False
    is_staff = False
    email = factory.Faker("email")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")

    class Meta:
        model = User
        skip_postgeneration_save = True


class LearningPathFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = LearningPath

    key = factory.Sequence(lambda n: LearningPathKey.from_string(f"path-v1:test+number{n}+run+group"))
    uuid = factory.Faker("uuid4")
    display_name = FuzzyText()
    description = FuzzyText()
    sequential = False


class LearningPathGradingCriteriaFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = LearningPathGradingCriteria

    learning_path = factory.SubFactory(LearningPathFactory)
    required_completion = 0.80
    required_grade = 0.75


class LearningPathStepFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = LearningPathStep

    learning_path = factory.SubFactory(LearningPathFactory)
    course_key = "course-v1:edX+DemoX+Demo_Course"
    order = factory.Sequence(lambda n: n + 1)
    weight = 1


class SkillFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Skill

    display_name = factory.Faker("word")


class RequiredSkillFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RequiredSkill

    learning_path = factory.SubFactory(LearningPathFactory)
    skill = factory.SubFactory(SkillFactory)
    level = factory.Faker("random_int", min=1, max=5)


class AcquiredSkillFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AcquiredSkill

    learning_path = factory.SubFactory(LearningPathFactory)
    skill = factory.SubFactory(SkillFactory)
    level = factory.Faker("random_int", min=1, max=5)


class LearningPathEnrollmentFactory(factory.django.DjangoModelFactory):
    """
    Factory for LearningPathEnrollment model.
    """

    user = factory.SubFactory(UserFactory)
    learning_path = factory.SubFactory(LearningPathFactory)
    is_active = True
    enrolled_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))

    class Meta:
        model = LearningPathEnrollment


class LearningPathEnrollmentAllowedFactory(factory.django.DjangoModelFactory):
    """
    Factory for LearningPathEnrollmentAllowed model.
    """

    email = factory.Faker("email")
    learning_path = factory.SubFactory(LearningPathFactory)
    user = None

    class Meta:
        model = LearningPathEnrollmentAllowed
