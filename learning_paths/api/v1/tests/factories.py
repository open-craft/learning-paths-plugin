# pylint: disable=missing-module-docstring,missing-class-docstring
import factory
from django.contrib import auth
from factory.fuzzy import FuzzyText

from learning_paths.models import LearningPath, LearningPathGradingCriteria

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
    required_completion = 100.0
    required_grade = 0.75
