# pylint: disable=missing-module-docstring,missing-class-docstring
import factory
from django.contrib import auth
from factory.fuzzy import FuzzyText

from learning_paths.keys import LearningPathKey
from learning_paths.models import (
    AcquiredSkill,
    LearningPath,
    LearningPathEnrollment,
    LearningPathEnrollmentAllowed,
    LearningPathEnrollmentAudit,
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


class AuditAttributeMixin:
    """Mixin for factory classes that need to handle the _audit attribute before saving."""

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """A custom create method to handle _audit attribute before the first save."""
        audit_data = kwargs.pop("_audit", None)
        instance = model_class(*args, **kwargs)
        if audit_data is not None:
            instance._audit = audit_data  # pylint: disable=protected-access

        instance.save()
        return instance


class LearningPathEnrollmentFactory(AuditAttributeMixin, factory.django.DjangoModelFactory):
    """
    Factory for LearningPathEnrollment model.
    """

    user = factory.SubFactory(UserFactory)
    learning_path = factory.SubFactory(LearningPathFactory)
    is_active = True

    class Meta:
        model = LearningPathEnrollment


class LearningPathEnrollmentAllowedFactory(AuditAttributeMixin, factory.django.DjangoModelFactory):
    """
    Factory for LearningPathEnrollmentAllowed model.
    """

    email = factory.Faker("email")
    learning_path = factory.SubFactory(LearningPathFactory)
    user = None
    is_active = True

    class Meta:
        model = LearningPathEnrollmentAllowed


class LearningPathEnrollmentAuditFactory(factory.django.DjangoModelFactory):
    """
    Factory for LearningPathEnrollmentAudit model.
    """

    enrolled_by = factory.SubFactory(UserFactory)
    enrollment = None
    enrollment_allowed = None
    state_transition = LearningPathEnrollmentAudit.DEFAULT_TRANSITION_STATE
    reason = factory.Faker("sentence")
    org = factory.Faker("company")
    role = factory.Faker("job")

    class Meta:
        model = LearningPathEnrollmentAudit
