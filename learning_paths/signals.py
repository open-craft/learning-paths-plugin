
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from .compat import CourseEnrollment
from .models import LearningPathCourseEnrollment, LearningPathStep, LearningPathEnrollment

logger = logging.getLogger(__name__)

@receiver(post_save, sender=CourseEnrollment)
def create_learningpath_course_enrollment(sender, instance, created, **kwargs):
    if created:  # Only react to new enrollments
        course_key = instance.course_id

        # Find the corresponding LearningPathStep (if it exists)
        try:
            learning_path_step = LearningPathStep.objects.get(course_key=course_key)
        except LearningPathStep.DoesNotExist:
            logger.info('Course is not part of any Learning Path. Ignoring.')
            return

        # Find the associated LearningPathEnrollment
        try:
            learning_path_enrollment = LearningPathEnrollment.objects.get(
                learning_path=learning_path_step.learning_path,
                user=instance.user
            )
        except LearningPathEnrollment.DoesNotExist:
            logger.warning('User is not enrolled in the relevant Learning Path.')
            return

        # Create the LearningPathCourseEnrollment object
        LearningPathCourseEnrollment.objects.create(
            learning_path_enrollment=learning_path_enrollment,
            course_key=course_key,
            status=LearningPathCourseEnrollment.ACTIVE,
            course_enrollment=instance
        )
