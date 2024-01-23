"""
Database models for learning_paths.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from model_utils.models import TimeStampedModel
from opaque_keys.edx.django.models import CourseKeyField

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

    slug = models.SlugField(
        db_index=True,
        unique=True,
        help_text=_("Custom unique code identifying this Learning Path."),
    )
    display_name = models.CharField(max_length=255)
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
        verbose_name=_("Is sequential"),
        help_text=_(
            "Whether the courses in this Learning Path are meant to be taken sequentially."
        ),
    )

    def __str__(self):
        """User-friendly string representation of this model."""
        return self.display_name


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
    relative_due_date_in_days = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_("Due date (days)"),
        help_text=_(
            "Used to calculate the due date from the starting date of the course."
        ),
    )
    order = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_("Sequential order"),
        help_text=_(
            "Ordinal position of this step in the sequence of the Learning Path, if applicable."
        ),
    )

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
