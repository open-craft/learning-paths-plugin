"""Django signal handler for learning paths plugin."""

# pylint: disable=unused-argument

import logging

from django.db import IntegrityError
from django.db.models.signals import post_save
from django.dispatch import receiver

from learning_paths.models import (
    LearningPathEnrollment,
    LearningPathEnrollmentAllowed,
    LearningPathEnrollmentAudit,
)

logger = logging.getLogger(__name__)


def process_pending_enrollments(sender, instance, created, **kwargs):
    """
    Process pending enrollments after a user instance has been created.

    Bulk enrollment API allows enrolling users with just the email. So learners who
    do not have an account yet would also be enrolled. This information is stored
    in the LearningPathEnrollmentAllowed model. This signal handler processes such
    instances and created the corresponding LearningPathEnrollment objects.

    Args:
        sender: User model class.
        instance: The actual instance being saved.
        created: A boolean indicating whether this is a creation and not an update.
    """
    if not created:
        logger.debug(
            "[LearningPaths] Skipping processing of pending enrollments for user %s.",
            instance,
        )
        return

    logger.info("[LearningPaths] Processing pending enrollments for user %s", instance)
    pending_enrollments = LearningPathEnrollmentAllowed.objects.filter(email=instance.email, is_active=True)
    enrollments_created = 0

    for entry in pending_enrollments:
        try:
            audit_data = {
                "enrolled_by": instance,
                "state_transition": LearningPathEnrollmentAudit.ALLOWEDTOENROLL_TO_ENROLLED,
            }
            if last_allowed_audit := entry.audit.order_by("-created").first():
                for field in ["reason", "org", "role"]:
                    audit_data[field] = getattr(last_allowed_audit, field, "")

            enrollment = LearningPathEnrollment(learning_path=entry.learning_path, user=instance)
            enrollment._audit = audit_data  # pylint: disable=protected-access
            enrollment.save()
            enrollments_created += 1

            # Link existing audits from the "allowed to enroll" entry to the new enrollment.
            entry.audit.update(enrollment=enrollment)

        except IntegrityError:  # pragma: no cover
            logger.info(
                "[LearningPaths] Enrollment already exists for user %s in the learning path %s",
                instance,
                entry.learning_path.key,
            )
        finally:
            entry.is_active = False
            entry.user = instance
            entry.save()

    logger.info(
        "[LearningPaths] Processed %d pending Learning Path enrollments for user %s.",
        enrollments_created,
        instance,
    )


def _create_enrollment_audit(instance: LearningPathEnrollment | LearningPathEnrollmentAllowed, audit_data: dict):
    """Create an audit record for the given instance with the provided audit data."""
    # If a previous audit exists, copy over missing fields
    previous_audit = instance.audit.order_by("-created").first()
    if previous_audit:
        for field in ["reason", "org", "role"]:
            if not audit_data.get(field):
                audit_data[field] = getattr(previous_audit, field)

    instance.audit.create(
        state_transition=audit_data.get("state_transition"),
        enrolled_by=audit_data.get("enrolled_by"),
        reason=audit_data.get("reason", ""),
        org=audit_data.get("org", ""),
        role=audit_data.get("role", ""),
    )


@receiver(post_save, sender=LearningPathEnrollment)
def create_enrollment_audit(sender, instance, created, **kwargs):
    """Create audit records when LearningPathEnrollment is saved."""
    audit_data = getattr(instance, "_audit", {})

    # Determine state transition if not provided
    if "state_transition" not in audit_data:
        if created:
            audit_data["state_transition"] = LearningPathEnrollmentAudit.UNENROLLED_TO_ENROLLED
        elif instance.is_active and not instance.tracker.previous("is_active"):
            audit_data["state_transition"] = LearningPathEnrollmentAudit.UNENROLLED_TO_ENROLLED
        elif not instance.is_active and instance.tracker.previous("is_active"):
            audit_data["state_transition"] = LearningPathEnrollmentAudit.ENROLLED_TO_UNENROLLED
        elif instance.is_active and instance.tracker.previous("is_active"):
            audit_data["state_transition"] = LearningPathEnrollmentAudit.ENROLLED_TO_ENROLLED
        elif not instance.is_active and not instance.tracker.previous("is_active"):
            audit_data["state_transition"] = LearningPathEnrollmentAudit.UNENROLLED_TO_UNENROLLED
        else:  # pragma: no cover
            # No relevant state change. This should not happen.
            audit_data["state_transition"] = LearningPathEnrollmentAudit.DEFAULT_TRANSITION_STATE

    _create_enrollment_audit(instance, audit_data)


@receiver(post_save, sender=LearningPathEnrollmentAllowed)
def create_enrollment_allowed_audit(sender, instance, created, **kwargs):
    """Create audit records when LearningPathEnrollmentAllowed is saved."""
    # The audit data can be missing in the following scenarios:
    # 1. The instance is created with `get_or_create`, so we want to provide this data later.
    # 2. The instance is updated when the user creates an account. In this case, the audit record is already created for
    #    the enrollment record, so we do not need to create it here.
    if not (audit_data := getattr(instance, "_audit", {})):
        return

    audit_data.setdefault("state_transition", LearningPathEnrollmentAudit.UNENROLLED_TO_ALLOWEDTOENROLL)

    audit_data["state_transition"] = audit_data.get(
        "state_transition", LearningPathEnrollmentAudit.UNENROLLED_TO_ALLOWEDTOENROLL
    )

    _create_enrollment_audit(instance, audit_data)
