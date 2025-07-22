"""
Database models for learning_paths.
"""

import logging
import os
import uuid
from datetime import datetime
from uuid import uuid4

from django.contrib import auth
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import OuterRef, Q
from django.utils.translation import gettext_lazy as _
from model_utils import FieldTracker
from model_utils.models import TimeStampedModel
from opaque_keys.edx.django.models import CourseKeyField
from slugify import slugify

from .compat import get_course_dates, get_user_course_grade
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
        Return only learning paths that should be visible to the given user with an enrollment date.

        For staff users: all learning paths.
        For non-staff: non-invite-only paths or invite-only paths they're enrolled in.

        Each learning path in the queryset is annotated with `enrollment_date` indicating
        the date when the user enrolled in that learning path (None if not enrolled).
        Results are ordered by enrollment date (the most recent first), with non-enrolled paths at the end.
        """
        queryset = self.get_queryset()

        # Annotate each path with the enrollment date.
        enrollment_subquery = LearningPathEnrollment.objects.filter(
            learning_path=OuterRef("pk"), user=user, is_active=True
        ).values("created")[:1]
        queryset = queryset.annotate(enrollment_date=models.Subquery(enrollment_subquery))

        # Apply visibility filtering based on the user role.
        if not user.is_staff:
            queryset = queryset.filter(Q(invite_only=False) | Q(enrollment_date__isnull=False))

        # Order by enrollment date (the most recent first), with null values at the end.
        return queryset.order_by(models.F("enrollment_date").desc(nulls_last=True))


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
        upload_to=_learning_path_image_upload_path,  # type: ignore
        blank=True,
        null=True,
        verbose_name=_("Image"),
        help_text=_("Image representing this Learning Path."),
    )
    level = models.CharField(max_length=255, blank=True, choices=LEVEL_CHOICES)
    duration = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Approximate time it should take to complete this Learning Path. Example: '10 Weeks'."),
    )
    time_commitment = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Approximate time commitment. Example: '4-6 hours/week'."),
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

    steps: "models.Manager[LearningPathStep]"
    requiredskill_set: "models.Manager[RequiredSkill]"
    acquiredskill_set: "models.Manager[AcquiredSkill]"
    grading_criteria: "LearningPathGradingCriteria"

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
    def course_dates(self) -> tuple[datetime | None, datetime | None]:
        """Retrieve the due date for this course."""
        return get_course_dates(self.course_key)

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
    level = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text=_("The skill level associated with this course."),
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
    tracker = FieldTracker(fields=["is_active"])

    def __str__(self):
        """User-friendly string representation of this model."""
        return "{}: {}".format(self.user, self.learning_path)


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


class LearningPathEnrollmentAllowed(TimeStampedModel):
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

    email = models.EmailField(db_index=True)
    learning_path = models.ForeignKey(LearningPath, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text=_("Indicates if the enrollment allowance is active"),
    )

    def __str__(self):
        """User-friendly string representation of this model."""
        return f"LearningPathEnrollmentAllowed for {self.email} in {self.learning_path.key}"


class LearningPathEnrollmentAudit(TimeStampedModel):
    """
    Audit model for tracking changes to learning path enrollments.

    .. no_pii:
    """

    # State transition constants (copied from edx-platform to maintain consistency)
    UNENROLLED_TO_ALLOWEDTOENROLL = "from unenrolled to allowed to enroll"
    ALLOWEDTOENROLL_TO_ENROLLED = "from allowed to enroll to enrolled"
    ENROLLED_TO_ENROLLED = "from enrolled to enrolled"
    ENROLLED_TO_UNENROLLED = "from enrolled to unenrolled"
    UNENROLLED_TO_ENROLLED = "from unenrolled to enrolled"
    ALLOWEDTOENROLL_TO_UNENROLLED = "from allowed to enroll to unenrolled"
    UNENROLLED_TO_UNENROLLED = "from unenrolled to unenrolled"
    DEFAULT_TRANSITION_STATE = "N/A"

    TRANSITION_STATES = (
        (UNENROLLED_TO_ALLOWEDTOENROLL, UNENROLLED_TO_ALLOWEDTOENROLL),
        (ALLOWEDTOENROLL_TO_ENROLLED, ALLOWEDTOENROLL_TO_ENROLLED),
        (ENROLLED_TO_ENROLLED, ENROLLED_TO_ENROLLED),
        (ENROLLED_TO_UNENROLLED, ENROLLED_TO_UNENROLLED),
        (UNENROLLED_TO_ENROLLED, UNENROLLED_TO_ENROLLED),
        (ALLOWEDTOENROLL_TO_UNENROLLED, ALLOWEDTOENROLL_TO_UNENROLLED),
        (UNENROLLED_TO_UNENROLLED, UNENROLLED_TO_UNENROLLED),
        (DEFAULT_TRANSITION_STATE, DEFAULT_TRANSITION_STATE),
    )

    enrolled_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, related_name="learning_path_audit")
    enrollment = models.ForeignKey(
        LearningPathEnrollment,
        on_delete=models.CASCADE,
        null=True,
        related_name="audit",
    )
    enrollment_allowed = models.ForeignKey(
        LearningPathEnrollmentAllowed,
        on_delete=models.CASCADE,
        null=True,
        related_name="audit",
    )
    state_transition = models.CharField(max_length=255, choices=TRANSITION_STATES, default=DEFAULT_TRANSITION_STATE)
    reason = models.TextField(blank=True)
    org = models.CharField(max_length=255, blank=True, db_index=True)
    role = models.CharField(max_length=255, blank=True)

    def __str__(self):
        """User-friendly string representation of this model."""
        enrollee = "unknown"
        learning_path = "unknown"

        if self.enrollment:
            enrollee = self.enrollment.user
            learning_path = self.enrollment.learning_path.key
        elif self.enrollment_allowed:
            enrollee = self.enrollment_allowed.user or self.enrollment_allowed.email
            learning_path = self.enrollment_allowed.learning_path.key

        return f"{self.state_transition} for {enrollee} in {learning_path}"
