"""Django signal handler for learning paths plugin."""

# pylint: disable=unused-argument

import logging

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
    Process pending enrollments when a user becomes able to claim them.

    Bulk enrollment API allows enrolling users with just the email. So learners who
    do not have an account yet would also be enrolled. This information is stored
    in the LearningPathEnrollmentAllowed model. This signal handler processes such
    instances and creates the corresponding LearningPathEnrollment objects.

    The entries are processed only for active users (i.e., users who confirmed their email address) when:
    1. The user is created (e.g., when the account is created already activated).
    2. The user activates the account.
    3. The user changes the email address (the change is applied after confirming the new email address).

    Args:
        sender: User model class.
        instance: The actual instance being saved.
        created: A boolean indicating whether this is a creation and not an update.
    """
    # `_changed_fields` is set by the `pre_save` receiver of the User model in edx-platform.
    changed_fields = getattr(instance, "_changed_fields", {})
    if not instance.is_active or not (created or {"email", "is_active"} & changed_fields.keys()):
        return

    process_pending_enrollments_for_user(instance)


def process_pending_enrollments_for_user(user) -> int:
    """
    Process the LearningPathEnrollmentAllowed entries matching the user's email.

    Active entries are converted into enrollments, unless the user already has an enrollment (active or not) in the
    learning path. All entries that are not linked to any user yet are deactivated and linked to the user, so they
    cannot be claimed by another account that changes its email to the same address.

    Returns:
        The number of created enrollments.
    """
    logger.info("[LearningPaths] Processing pending enrollments for user %s", user)
    pending_enrollments = LearningPathEnrollmentAllowed.objects.filter(email=user.email, user__isnull=True)
    enrollments_created = 0

    for entry in pending_enrollments:
        enrollment_exists = LearningPathEnrollment.objects.filter(learning_path=entry.learning_path, user=user).exists()

        if entry.is_active and not enrollment_exists:
            audit_data = {
                "enrolled_by": user,
                "state_transition": LearningPathEnrollmentAudit.ALLOWEDTOENROLL_TO_ENROLLED,
            }
            if last_allowed_audit := entry.audit.order_by("-created").first():
                for field in ["reason", "org", "role"]:
                    audit_data[field] = getattr(last_allowed_audit, field, "")

            enrollment = LearningPathEnrollment(learning_path=entry.learning_path, user=user)
            enrollment._audit = audit_data  # pylint: disable=protected-access
            enrollment.save()
            enrollments_created += 1

            # Link existing audits from the "allowed to enroll" entry to the new enrollment.
            entry.audit.update(enrollment=enrollment)
        elif entry.is_active:
            logger.info(
                "[LearningPaths] Enrollment already exists for user %s in the learning path %s",
                user,
                entry.learning_path.key,
            )

        entry.is_active = False
        entry.user = user
        entry.save()

    logger.info(
        "[LearningPaths] Processed %d pending Learning Path enrollments for user %s.",
        enrollments_created,
        user,
    )
    return enrollments_created


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
