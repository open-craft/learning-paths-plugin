# pylint: disable=missing-module-docstring,missing-class-docstring
import factory
from django.contrib import auth
from factory.fuzzy import FuzzyText

from learning_paths.models import (
    AcquiredSkill,
    LearningPath,
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


class LearnerPathwayFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = LearningPath

    uuid = factory.Faker("uuid4")
    display_name = FuzzyText()
    slug = FuzzyText()
    display_name = FuzzyText()
    description = FuzzyText()
    sequential = False


class LearnerPathGradingCriteriaFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = LearningPathGradingCriteria

    learning_path = factory.SubFactory(LearnerPathwayFactory)
    required_completion = 0.80
    required_grade = 0.75


class LearningPathStepFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = LearningPathStep

    learning_path = factory.SubFactory(LearnerPathwayFactory)
    course_key = "course-v1:edX+DemoX+Demo_Course"
    relative_due_date_in_days = factory.Faker("random_int", min=1, max=30)
    order = factory.Sequence(lambda n: n + 1)
    weight = 1


class SkillFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Skill

    display_name = factory.Faker("word")


class RequiredSkillFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RequiredSkill

    learning_path = factory.SubFactory(LearnerPathwayFactory)
    skill = factory.SubFactory(SkillFactory)
    level = factory.Faker("random_int", min=1, max=5)


class AcquiredSkillFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AcquiredSkill

    learning_path = factory.SubFactory(LearnerPathwayFactory)
    skill = factory.SubFactory(SkillFactory)
    level = factory.Faker("random_int", min=1, max=5)
