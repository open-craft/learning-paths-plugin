"""
Django Admin for learning_paths.
"""

import os

from django import forms
from django.contrib import admin, auth, messages
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django_object_actions import DjangoObjectActions, action

from .compat import get_course_keys_with_outlines
from .models import (
    AcquiredSkill,
    LearningPath,
    LearningPathEnrollment,
    LearningPathEnrollmentAllowed,
    LearningPathEnrollmentAudit,
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
        self.fields["course_key"].widget = CourseKeyDatalistWidget(choices=self._course_keys)

    course_key = forms.CharField(label=_("Course"))

    def clean_course_key(self):
        """Validate that the course key is on the list of available course keys."""
        course_key = self.cleaned_data.get("course_key")
        valid_keys = {str(key).strip() for key in self._course_keys}

        if course_key not in valid_keys:
            raise ValidationError(_("Invalid course key. Please select a course from the suggestions."))

        return course_key


class LearningPathStepInline(admin.TabularInline):
    """Inline Admin for Learning Path step."""

    model = LearningPathStep
    form = LearningPathStepForm
    fields = ("course_key",)


class AcquiredSkillInline(admin.TabularInline):
    """Inline Admin for Learning Path acquired skill."""

    model = AcquiredSkill


class RequiredSkillInline(admin.TabularInline):
    """Inline Admin for Learning Path required skill."""

    model = RequiredSkill


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
            raise ValidationError(f"The following usernames are not valid: {', '.join(invalid_usernames)}")
        return users


@admin.register(LearningPath)
class LearningPathAdmin(DjangoObjectActions, admin.ModelAdmin):
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
        "duration",
        "invite_only",
    )
    list_filter = ("invite_only",)

    inlines = [
        LearningPathStepInline,
        RequiredSkillInline,
        AcquiredSkillInline,
    ]

    change_actions = ("duplicate_learning_path",)

    def save_related(self, request, form, formsets, change):
        """Save related objects and enroll users in the learning path."""
        super().save_related(request, form, formsets, change)
        with transaction.atomic():
            for user in form.cleaned_data["usernames"]:
                LearningPathEnrollment.objects.get_or_create(user=user, learning_path=form.instance)

    @action(label="Duplicate Learning Path", description="Create a copy of this Learning Path")
    def duplicate_learning_path(self, request, obj: LearningPath) -> HttpResponseRedirect:
        """Duplicate the learning path with a new unique key."""
        base_new_key = f"{str(obj.key)}_copy"
        new_key = base_new_key
        counter = 1

        while LearningPath.objects.filter(key=new_key).exists():
            new_key = f"{base_new_key}_{counter}"
            counter += 1

        with transaction.atomic():
            new_learning_path = LearningPath(
                key=new_key,
                display_name=f"{obj.display_name} (Copy)",
                subtitle=obj.subtitle,
                description=obj.description,
                level=obj.level,
                duration=obj.duration,
                time_commitment=obj.time_commitment,
                sequential=obj.sequential,
                invite_only=obj.invite_only,
            )

            if obj.image:
                with obj.image.open("rb") as original_file:
                    image_content = original_file.read()

                original_filename = os.path.basename(obj.image.name)
                new_learning_path.image.save(original_filename, ContentFile(image_content), save=False)

            new_learning_path.save()

            new_learning_path.refresh_from_db()
            new_learning_path.grading_criteria.required_completion = obj.grading_criteria.required_completion
            new_learning_path.grading_criteria.required_grade = obj.grading_criteria.required_grade
            new_learning_path.grading_criteria.save()

            for step in obj.steps.all():
                step.pk = None
                step.learning_path = new_learning_path
                step.save()

            for skill in obj.requiredskill_set.all():
                skill.pk = None
                skill.learning_path = new_learning_path
                skill.save()

            for skill in obj.acquiredskill_set.all():
                skill.pk = None
                skill.learning_path = new_learning_path
                skill.save()

        messages.success(request, f"Learning path duplicated successfully. New key: {new_key}")
        return HttpResponseRedirect(reverse("admin:learning_paths_learningpath_change", args=[new_learning_path.pk]))


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    """Admin for Learning Path generic skill."""

    model = Skill


class EnrollmentAuditInline(admin.TabularInline):
    """Inline admin for LearningPathEnrollmentAudit records."""

    model = LearningPathEnrollmentAudit
    fk_name = "enrollment"
    extra = 0
    exclude = ["enrollment_allowed"]
    readonly_fields = [
        "state_transition",
        "enrolled_by",
        "reason",
        "org",
        "role",
        "created",
    ]

    def has_add_permission(self, request, obj=None):
        """Disable manual creation of audit records."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Disable deletion of audit records."""
        return False


class EnrollmentAllowedAuditInline(admin.TabularInline):
    """Inline admin for LearningPathEnrollmentAudit records related to enrollment allowed."""

    model = LearningPathEnrollmentAudit
    fk_name = "enrollment_allowed"
    extra = 0
    exclude = ["enrollment"]
    readonly_fields = [
        "state_transition",
        "enrolled_by",
        "reason",
        "org",
        "role",
        "created",
    ]

    def has_add_permission(self, request, obj=None):
        """Disable manual creation of audit records."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Disable deletion of audit records."""
        return False


@admin.register(LearningPathEnrollment)
class EnrolledUsersAdmin(admin.ModelAdmin):
    """Admin for Learning Path enrollment."""

    model = LearningPathEnrollment
    raw_id_fields = ("user",)
    autocomplete_fields = ["learning_path"]
    inlines = [EnrollmentAuditInline]

    list_display = [
        "id",
        "user",
        "learning_path",
        "is_active",
        "created",
    ]

    list_filter = [
        "learning_path__key",
        "created",
        "is_active",
    ]

    search_fields = [
        "id",
        "user__username",
        "learning_path__key",
        "learning_path__display_name",
    ]


@admin.register(LearningPathEnrollmentAllowed)
class EnrollmentAllowedAdmin(admin.ModelAdmin):
    """Admin configuration for LearningPathEnrollmentAllowed model."""

    list_display = [
        "id",
        "email",
        "get_user",
        "learning_path",
        "created",
    ]

    list_filter = [
        "learning_path",
        "created",
    ]

    search_fields = [
        "email",
        "user__username",
        "user__email",
        "learning_path__key",
    ]

    readonly_fields = [
        "user",
        "created",
        "modified",
    ]

    inlines = [EnrollmentAllowedAuditInline]

    def get_user(self, obj):
        """Get the associated user, if any."""
        return obj.user.username if obj.user else "-"

    get_user.short_description = "User"


@admin.register(LearningPathEnrollmentAudit)
class EnrollmentAuditAdmin(admin.ModelAdmin):
    """Admin configuration for LearningPathEnrollmentAudit model."""

    list_display = [
        "id",
        "state_transition",
        "enrolled_by",
        "get_enrollee",
        "get_learning_path",
        "created",
        "org",
        "role",
    ]

    list_filter = [
        "state_transition",
        "created",
        "org",
        "role",
    ]

    search_fields = [
        "enrolled_by__username",
        "enrolled_by__email",
        "enrollment__user__username",
        "enrollment__user__email",
        "enrollment_allowed__email",
        "enrollment__learning_path__key",
        "enrollment_allowed__learning_path__key",
        "reason",
    ]

    readonly_fields = [
        "enrollment",
        "enrollment_allowed",
        "enrolled_by",
        "state_transition",
        "created",
        "modified",
    ]

    def get_enrollee(self, obj):
        """Get the enrollee (user or email)."""
        if obj.enrollment:
            return obj.enrollment.user.username
        elif obj.enrollment_allowed:
            return obj.enrollment_allowed.user.username if obj.enrollment_allowed.user else obj.enrollment_allowed.email
        return "-"

    get_enrollee.short_description = "Enrollee"

    def get_learning_path(self, obj):
        """Get the learning path title."""
        if obj.enrollment:
            return obj.enrollment.learning_path.key
        elif obj.enrollment_allowed:
            return obj.enrollment_allowed.learning_path.key
        return "-"

    get_learning_path.short_description = "Learning Path"
