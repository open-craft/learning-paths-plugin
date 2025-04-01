"""Django signal handler for learning paths plugin."""

import logging

from learning_paths.models import LearningPathEnrollment, LearningPathEnrollmentAllowed

logger = logging.getLogger(__name__)


def process_pending_enrollments(
    sender, instance, created, **kwargs
):  # pylint: disable=unused-argument
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
    pending_enrollments = LearningPathEnrollmentAllowed.objects.filter(
        email=instance.email
    ).all()

    enrollments = []

    for entry in pending_enrollments:
        entry.user = instance
        entry.save()

        enrollments.append(
            LearningPathEnrollment(learning_path=entry.learning_path, user=instance)
        )
    new_enrollments = LearningPathEnrollment.objects.bulk_create(enrollments)
    logger.info(
        "[LearningPaths] Processed %d pending Learning Path enrollments for user %s.",
        instance,
        len(new_enrollments),
    )
