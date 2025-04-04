"""
Database models for learning_paths.
"""

from datetime import datetime, timedelta
from uuid import uuid4

from django.contrib import auth
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from model_utils.models import TimeStampedModel
from opaque_keys.edx.django.models import CourseKeyField
from simple_history.models import HistoricalRecords

from .compat import get_course_due_date, get_user_course_grade
from .keys import LearningPathKeyField

User = auth.get_user_model()

LEVEL_CHOICES = [
    ("beginner", _("Beginner")),
    ("intermediate", _("Intermediate")),
    ("advanced", _("Advanced")),
]


class LearningPath(TimeStampedModel):
    """
    A Learning Path, containing a sequence of courses.

    .. no_pii:
    """

    key = LearningPathKeyField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text=_(
            "Unique identifier for this Learning Path.<br/>"
            "It must follow the format: <i>path-v1:{org}+{number}+{run}+{group}</i>."
        ),
    )
    # LearningPath is consumed as a course-discovery Program.
    # Programs are identified by UUIDs, which is why we must have this UUID field.
    uuid = models.UUIDField(
        blank=True,
        default=uuid4,
        editable=False,
        unique=True,
        help_text=_("Legacy identifier for compatibility with Course Discovery."),
    )
    slug = models.SlugField(
        db_index=True,
        unique=True,
        help_text=_("Custom unique code identifying this Learning Path."),
    )
    display_name = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    # We don't use URLField here in order to allow e.g. relative URLs.
    # max_length=200 as from URLField.
    image_url = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_("Image URL"),
        help_text=_("URL to an image representing this Learning Path."),
    )
    level = models.CharField(max_length=255, blank=True, choices=LEVEL_CHOICES)
    duration_in_days = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_("Duration (days)"),
        help_text=_(
            "Approximate time (in days) it should take to complete this Learning Path."
        ),
    )
    sequential = models.BooleanField(
        default=False,
        verbose_name=_("Is sequential"),
        help_text=_(
            "Whether the courses in this Learning Path are meant to be taken sequentially."
        ),
    )
    enrolled_users = models.ManyToManyField(User, through="LearningPathEnrollment")

    def __str__(self):
        """User-friendly string representation of this model."""
        return self.display_name

    def save(self, *args, **kwargs):
        """Create default grading criteria when a new learning path is created."""
        is_new = self._state.adding
        super().save(*args, **kwargs)

        if is_new and not hasattr(self, "grading_criteria"):
            LearningPathGradingCriteria.objects.get_or_create(learning_path=self)


class LearningPathStep(TimeStampedModel):
    """
    A step in a Learning Path, consisting of a course and an ordinal position.

    .. no_pii:
    """

    class Meta:
        """Model options."""

        unique_together = ("learning_path", "course_key")

    course_key = CourseKeyField(max_length=255)
    learning_path = models.ForeignKey(
        LearningPath, related_name="steps", on_delete=models.CASCADE
    )
    order = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_("Sequential order"),
        help_text=_(
            "Ordinal position of this step in the sequence of the Learning Path, if applicable."
        ),
    )
    weight = models.FloatField(
        default=1.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text=_(
            "Weight of this course in the learning path's aggregate grade."
            "Specify as a floating point number between 0 and 1, where 1 represents 100%."
        ),
    )

    @property
    def due_date(self) -> datetime | None:
        """Retrieve the due date for this course."""
        return get_course_due_date(self.course_key)

    def __str__(self):
        """User-friendly string representation of this model."""
        return "{}: {}".format(self.order, self.course_key)


class Skill(TimeStampedModel):
    """
    A skill that can be associated with Learning Paths.

    .. no_pii:
    """

    display_name = models.CharField(max_length=255)

    def __str__(self):
        """User-friendly string representation of this model."""
        return self.display_name


class LearningPathSkill(TimeStampedModel):
    """
    Abstract base model for a skill required or acquired in a Learning Path..

    .. no_pii:
    """

    class Meta:
        """Model options."""

        abstract = True
        unique_together = ("learning_path", "skill")

    learning_path = models.ForeignKey(LearningPath, on_delete=models.CASCADE)
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)
    level = models.PositiveIntegerField(
        help_text=_("The skill level associated with this course.")
    )

    def __str__(self):
        """User-friendly string representation of this model."""
        return "{}: {}".format(self.skill, self.level)


class RequiredSkill(LearningPathSkill):
    """
    A required skill for a Learning Path.

    .. no_pii:
    """


class AcquiredSkill(LearningPathSkill):
    """
    A skill acquired in a Learning Path.

    .. no_pii:
    """


class LearningPathEnrollment(TimeStampedModel):
    """
    A user enrolled in a Learning Path.

    .. no_pii:
    """

    class Meta:
        """Model options."""

        unique_together = ("user", "learning_path")

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    learning_path = models.ForeignKey(LearningPath, on_delete=models.CASCADE)
    is_active = models.BooleanField(
        default=True,
        help_text=_("Indicates if the learner is enrolled or not in the Learning Path"),
    )
    enrolled_at = models.DateTimeField(
        auto_now_add=True,
        help_text=_(
            "Timestamp of enrollment or un-enrollment. To be explicitly set when performing"
            " a learner enrollment."
        ),
    )

    history = HistoricalRecords()

    def __str__(self):
        """User-friendly string representation of this model."""
        return "{}: {}".format(self.user, self.learning_path)

    @property
    def estimated_end_date(self):
        """Estimated end date of the learning path."""
        if self.learning_path.duration_in_days is None:
            return None
        return self.created + timedelta(days=self.learning_path.duration_in_days)


class LearningPathGradingCriteria(models.Model):
    """
    Grading criteria for a learning path.

    .. no_pii:
    """

    learning_path = models.OneToOneField(
        LearningPath, related_name="grading_criteria", on_delete=models.CASCADE
    )
    required_completion = models.FloatField(
        default=0.80,
        help_text=(
            "The minimum average completion (0.0-1.0) across all steps in the learning path "
            "required to mark it as completed."
        ),
    )
    required_grade = models.FloatField(
        default=0.75,
        help_text=(
            "Minimum weighted arithmetic mean grade (0.0-1.0) required across all steps "
            "to pass this learning path. The weight of each step is determined by its `weight` field."
        ),
    )

    def __str__(self):
        """User-friendly string representation of this model."""
        return f"{self.learning_path.display_name} Grading Criteria"

    def calculate_grade(self, user):
        """
        Calculate the aggregate grade for a user across the learning path.
        """
        total_weight = 0.0
        weighted_sum = 0.0

        for step in self.learning_path.steps.all():
            course_grade = get_user_course_grade(user, step.course_key)
            course_weight = step.weight
            weighted_sum += course_grade.percent * course_weight
            total_weight += course_weight

        return weighted_sum / total_weight if total_weight > 0 else 0.0


class LearningPathEnrollmentAllowed(models.Model):
    """
    Represents an allowed enrollment in a learning path for a user email.

    These objects can be created when learners are invited/enrolled by staff before
    they have registered and created an account, allowing future learners to enroll.

    .. pii: The email field is not retired to allow future learners to enroll.
    .. pii_types: email_address
    .. pii_retirement: retained
    """

    class Meta:
        """Model options."""

        unique_together = ("email", "learning_path")

    email = models.EmailField()
    learning_path = models.ForeignKey(LearningPath, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        """User-friendly string representation of this model."""
        return f"LearningPathEnrollmentAllowed for {self.user.username} in {self.learning_path.display_name}"
