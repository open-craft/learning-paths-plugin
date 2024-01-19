"""
Django Admin for learning_paths.
"""
from django.contrib import admin

from .models import AcquiredSkill, LearningPath, LearningPathStep, RequiredSkill, Skill


class LearningPathStepInline(admin.TabularInline):
    """Inline Admin for Learning Path step."""

    model = LearningPathStep


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
