"""
Django Admin for learning_paths.
"""

from django import forms
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .compat import get_course_keys_with_outlines
from .models import AcquiredSkill, LearningPath, LearningPathStep, RequiredSkill, Skill


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


class LearningPathAdmin(admin.ModelAdmin):
    """Admin for Learning Path."""

    model = LearningPath

    search_fields = [
        "slug",
        "display_name",
    ]
    list_display = (
        "uuid",
        "slug",
        "display_name",
        "level",
        "duration_in_days",
    )

    inlines = [
        LearningPathStepInline,
        RequiredSkillInline,
        AcquiredSkillInline,
    ]


class SkillAdmin(admin.ModelAdmin):
    """Admin for Learning Path generic skill."""

    model = Skill


admin.site.register(LearningPath, LearningPathAdmin)
admin.site.register(Skill, SkillAdmin)
