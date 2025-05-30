"""
Database models for learning_paths.
"""

import logging
import os
import uuid
from datetime import datetime, timedelta
from uuid import uuid4

from django.contrib import auth
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Exists, OuterRef, Q
from django.utils.translation import gettext_lazy as _
from model_utils import FieldTracker
from model_utils.models import TimeStampedModel
from opaque_keys.edx.django.models import CourseKeyField
from simple_history.models import HistoricalRecords
from slugify import slugify

from .compat import get_course_due_date, get_user_course_grade
from .keys import LearningPathKeyField

log = logging.getLogger(__name__)

User = auth.get_user_model()

LEVEL_CHOICES = [
    ("beginner", _("Beginner")),
    ("intermediate", _("Intermediate")),
    ("advanced", _("Advanced")),
]


class LearningPathManager(models.Manager):
    """Manager for LearningPath model that handles visibility rules."""

    def get_paths_visible_to_user(self, user: User) -> models.QuerySet:
        """
        Return only learning paths that should be visible to the given user with enrollment status.

        For staff users: all learning paths.
        For non-staff: non-invite-only paths or invite-only paths they're enrolled in.

        Each learning path in the queryset is annotated with `is_enrolled` indicating
        whether the user has an active enrollment in that learning path.
        """
        queryset = self.get_queryset()

        # Annotate each path with whether the user is enrolled.
        enrollment_exists = LearningPathEnrollment.objects.filter(
            learning_path=OuterRef("pk"), user=user, is_active=True
        )
        queryset = queryset.annotate(is_enrolled=Exists(enrollment_exists))

        # Apply visibility filtering based on the user role.
        if not user.is_staff:
            queryset = queryset.filter(Q(invite_only=False) | Q(is_enrolled=True))

        return queryset


class LearningPath(TimeStampedModel):
    """
    A Learning Path, containing a sequence of courses.

    .. no_pii:
    """

    def _learning_path_image_upload_path(self, filename: str) -> str:
        """
        Return the path where learning path images should be stored.

        Uses the learning path key with a random suffix to ensure cache invalidation.
        """
        _, extension = os.path.splitext(filename)
        random_suffix = uuid.uuid4().hex[:8]
        slugified_key = slugify(str(self.key))
        new_filename = f"{slugified_key}_{random_suffix}{extension}"
        return f"learning_paths/images/{new_filename}"

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
    display_name = models.CharField(max_length=255)
    subtitle = models.TextField(blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(
        upload_to=_learning_path_image_upload_path,
        blank=True,
        null=True,
        verbose_name=_("Image"),
        help_text=_("Image representing this Learning Path."),
    )
    level = models.CharField(max_length=255, blank=True, choices=LEVEL_CHOICES)
    duration_in_days = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_("Duration (days)"),
        help_text=_("Approximate time (in days) it should take to complete this Learning Path."),
    )
    sequential = models.BooleanField(
        default=False,
        verbose_name=_("Is sequential"),
        help_text=_("Whether the courses in this Learning Path are meant to be taken sequentially."),
    )
    # Note: the enrolled learners will be able to self-enroll in all courses
    # (steps) of the learning path. To avoid mistakes of making the courses
    # visible to all users, we decided to make the learning paths invite-only
    # by default. Making them public must be an explicit action.
    invite_only = models.BooleanField(
        default=True,
        verbose_name=_("Invite only"),
        help_text=_("If enabled, only staff can enroll users and only enrolled users can see the learning path."),
    )
    enrolled_users = models.ManyToManyField(User, through="LearningPathEnrollment")
    tracker = FieldTracker(fields=["image"])

    objects = LearningPathManager()

    def __str__(self):
        """User-friendly string representation of this model."""
        return str(self.key)

    def save(self, *args, **kwargs):
        """
        Perform the validation and cleanup when saving a Learning Path.

        This method performs the following actions:
        1. Check that the key is not empty.
        2. Create default grading criteria when a new learning path is created.
        3. Delete the old image if the image is changed.
        """
        if not self.key:
            raise ValidationError("Learning Path key cannot be empty.")

        if self.tracker.has_changed("image"):
            if old_image := self.tracker.previous("image"):
                try:
                    old_image.delete(save=False)
                except Exception as e:  # pylint: disable=broad-except
                    log.exception("Failed to delete old image: %s", e)

        is_new = self._state.adding
        super().save(*args, **kwargs)

        if is_new and not hasattr(self, "grading_criteria"):
            LearningPathGradingCriteria.objects.get_or_create(learning_path=self)

    def delete(self, *args, **kwargs):
        """Delete the image file when the learning path is deleted."""
        if self.image:
            try:
                self.image.delete(save=False)
            except Exception as e:  # pylint: disable=broad-except
                log.exception("Failed to delete image: %s", e)
        super().delete(*args, **kwargs)


class LearningPathStep(TimeStampedModel):
    """
    A step in a Learning Path, consisting of a course and an ordinal position.

    .. no_pii:
    """

    class Meta:
        """Model options."""

        unique_together = ("learning_path", "course_key")

    course_key = CourseKeyField(max_length=255)
    learning_path = models.ForeignKey(LearningPath, related_name="steps", on_delete=models.CASCADE)
    order = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_("Sequential order"),
        help_text=_("Ordinal position of this step in the sequence of the Learning Path, if applicable."),
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

    def save(self, *args, **kwargs):
        """Validate the course key before saving."""
        if not self.course_key:
            raise ValidationError("Course key cannot be empty.")

        super().save(*args, **kwargs)


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
    level = models.PositiveIntegerField(help_text=_("The skill level associated with this course."))

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
            "Timestamp of enrollment or un-enrollment. To be explicitly set when performing a learner enrollment."
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

    learning_path = models.OneToOneField(LearningPath, related_name="grading_criteria", on_delete=models.CASCADE)
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
