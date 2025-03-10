# pylint: disable=missing-module-docstring,missing-class-docstring
from datetime import datetime, timezone

import factory
from django.contrib import auth
from factory.fuzzy import FuzzyText

from learning_paths.keys import LearningPathKey
from learning_paths.models import (
    LearningPath,
    LearningPathEnrollment,
    LearningPathGradingCriteria,
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


class LearningPathFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = LearningPath

    key = factory.Sequence(
        lambda n: LearningPathKey.from_string(f"path-v1:test+number{n}+run+group")
    )
    uuid = factory.Faker("uuid4")
    display_name = FuzzyText()
    slug = FuzzyText()
    description = FuzzyText()
    sequential = False


class LearningPathGradingCriteriaFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = LearningPathGradingCriteria

    learning_path = factory.SubFactory(LearningPathFactory)
    required_completion = 0.80
    required_grade = 0.75


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
