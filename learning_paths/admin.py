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


class CourseKeyDatalistWidget(forms.TextInput):
    """A widget that provides a datalist for course keys."""

    def __init__(self, choices=None, attrs=None):
        """Initialize the widget with a datalist and apply styles."""
        attrs = attrs or {}
        attrs.update(
            {
                "style": "width: 30em;",
                "class": "form-control datalist-input",
                "placeholder": _("Type to search courses..."),
            }
        )
        super().__init__(attrs)
        self.choices = choices or []

    def render(self, name, value, attrs=None, renderer=None):
        """Render the widget with a datalist."""
        final_attrs = attrs or {}
        data_list_id = f"datalist_{name}"
        final_attrs["list"] = data_list_id

        text_input_html = super().render(name, value, attrs, renderer)
        data_list_id = f"datalist_{name}"
        options = "\n".join(f'<option value="{choice}" />' for choice in self.choices)
        datalist_html = f'<datalist id="{data_list_id}">\n{options}\n</datalist>'
        return f"{text_input_html}\n{datalist_html}"


class LearningPathStepForm(forms.ModelForm):
    """Form for Learning Path step."""

    def __init__(self, *args, **kwargs):
        """Lazily fetch course keys to avoid calling compat code in all environments."""
        super().__init__(*args, **kwargs)
        self._course_keys = get_course_keys_with_outlines()
        self.fields["course_key"].widget = CourseKeyDatalistWidget(
            choices=self._course_keys
        )

    course_key = forms.CharField(label=_("Course"))

    def clean_course_key(self):
        """Validate that the course key is on the list of available course keys."""
        course_key = self.cleaned_data.get("course_key")
        valid_keys = {str(key).strip() for key in self._course_keys}

        if course_key not in valid_keys:
            raise ValidationError(
                _("Invalid course key. Please select a course from the suggestions.")
            )

        return course_key


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
        "display_name",
        "key",
    ]
    list_display = (
        "key",
        "display_name",
        "level",
        "duration_in_days",
        "invite_only",
    )
    list_filter = ("invite_only",)
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
    raw_id_fields = ("user",)
    autocomplete_fields = ["learning_path"]

    search_fields = [
        "id",
        "user__username",
        "learning_path__key",
        "learning_path__display_name",
    ]


admin.site.register(LearningPath, LearningPathAdmin)
admin.site.register(Skill, SkillAdmin)
admin.site.register(LearningPathEnrollment, EnrolledUsersAdmin)
