"""
Django Admin for learning_paths.
"""

from django import forms
from django.contrib import admin, auth
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from .compat import get_course_keys_with_outlines
from .models import (
    AcquiredSkill,
    LearningPath,
    LearningPathEnrollment,
    LearningPathGradingCriteria,
    LearningPathStep,
    RequiredSkill,
    Skill,
)

User = auth.get_user_model()


def get_course_keys_choices():
    """Get course keys in an adequate format for a choice field."""
    yield None, ""
    for key in get_course_keys_with_outlines():
        yield key, key


class LearningPathStepForm(forms.ModelForm):
    """Admin form for Learning Path step."""

    # TODO: Use autocomplete select instead.
    # See <https://github.com/open-craft/section-to-course/blob/db6fd6f8f4478e91bb531e6c2fa50143e1c2e012/
    #      section_to_course/admin.py#L31-L140>
    course_key = forms.ChoiceField(choices=get_course_keys_choices, label=_("Course"))


class LearningPathStepInline(admin.TabularInline):
    """Inline Admin for Learning Path step."""

    model = LearningPathStep
    form = LearningPathStepForm


class AcquiredSkillInline(admin.TabularInline):
    """Inline Admin for Learning Path acquired skill."""

    model = AcquiredSkill


class RequiredSkillInline(admin.TabularInline):
    """Inline Admin for Learning Path required skill."""

    model = RequiredSkill


class LearningPathGradingCriteriaInline(admin.TabularInline):
    """Inline Admin for Learning path grading criteria."""

    model = LearningPathGradingCriteria


class BulkEnrollUsersForm(forms.ModelForm):
    """Form to bulk enroll users in a learning path."""

    usernames = forms.CharField(
        widget=forms.Textarea,
        help_text="Enter usernames separated by newlines",
        label="Bulk enroll users",
        required=False,
    )

    class Meta:
        """Form options."""

        model = LearningPath
        fields = "__all__"

    def clean_usernames(self):
        """Validate usernames and return a list of users."""
        data = self.cleaned_data["usernames"]
        if not data:
            return []
        usernames = [username.strip() for username in data.split("\n")]
        users = User.objects.filter(username__in=usernames)
        found_usernames = list(users.values_list("username", flat=True))
        invalid_usernames = set(usernames) - set(found_usernames)
        if invalid_usernames:
            raise ValidationError(
                f"The following usernames are not valid: {', '.join(invalid_usernames)}"
            )
        return users


class LearningPathAdmin(admin.ModelAdmin):
    """Admin for Learning Path."""

    model = LearningPath
    form = BulkEnrollUsersForm

    search_fields = [
        "slug",
        "display_name",
        "key",
    ]
    list_display = (
        "key",
        "slug",
        "display_name",
        "level",
        "duration_in_days",
    )
    readonly_fields = ("key",)

    inlines = [
        LearningPathStepInline,
        RequiredSkillInline,
        AcquiredSkillInline,
        LearningPathGradingCriteriaInline,
    ]

    def get_readonly_fields(self, request, obj=None):
        """Make key read-only only for existing objects."""
        if obj:  # Editing an existing object.
            return self.readonly_fields
        return ()  # Allow all fields during creation.

    def save_related(self, request, form, formsets, change):
        """Save related objects and enroll users in the learning path."""
        super().save_related(request, form, formsets, change)
        with transaction.atomic():
            for user in form.cleaned_data["usernames"]:
                LearningPathEnrollment.objects.get_or_create(
                    user=user, learning_path=form.instance
                )


class SkillAdmin(admin.ModelAdmin):
    """Admin for Learning Path generic skill."""

    model = Skill


class EnrolledUsersAdmin(admin.ModelAdmin):
    """Admin for Learning Path enrollment."""

    model = LearningPathEnrollment

    search_fields = [
        "id",
        "user__username",
        "learning_path__key",
        "learning_path__slug",
        "learning_path__display_name",
    ]


admin.site.register(LearningPath, LearningPathAdmin)
admin.site.register(Skill, SkillAdmin)
admin.site.register(LearningPathEnrollment, EnrolledUsersAdmin)
