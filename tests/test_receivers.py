"""Tests for the signals module."""

from django.contrib.auth import get_user_model
from django.test import TestCase

from learning_paths.api.v1.tests.factories import LearningPathFactory
from learning_paths.models import LearningPathEnrollment, LearningPathEnrollmentAllowed
from learning_paths.receivers import process_pending_enrollments

User = get_user_model()


class TestProcessPendingEnrollments(TestCase):
    """
    Tests for the process_pending_enrollments signal handler.
    """

    def setUp(self):
        self.user_email = "test@example.com"
        self.learning_path_1 = LearningPathFactory()
        self.learning_path_2 = LearningPathFactory()

    def test_process_pending_enrollments_with_pending_enrollments(self):
        """
        GIVEN that there are LearningPathEnrollmentAllowed objects for an email
        WHEN the process_pending_enrollments signal handler is triggered
        THEN actual enrollment objects are created for the user
        """
        pending_entry_1 = LearningPathEnrollmentAllowed.objects.create(
            email=self.user_email, learning_path=self.learning_path_1
        )
        pending_entry_2 = LearningPathEnrollmentAllowed.objects.create(
            email=self.user_email, learning_path=self.learning_path_2
        )
        user = User.objects.create(email=self.user_email)

        process_pending_enrollments(sender=User, instance=user, created=True)

        pending_entry_1.refresh_from_db()
        pending_entry_2.refresh_from_db()
        self.assertEqual(pending_entry_1.user, user)
        self.assertEqual(pending_entry_2.user, user)

        enrollments = LearningPathEnrollment.objects.all()
        self.assertEqual(len(enrollments), 2)
        self.assertTrue(all(e.user == user for e in enrollments))
        self.assertEqual(enrollments[0].learning_path, pending_entry_1.learning_path)
        self.assertEqual(enrollments[1].learning_path, pending_entry_2.learning_path)

    def test_process_pending_enrollments_when_no_pending_enrollments(self):
        """
        GIVEN that there are no LearningPathEnrollmentAllowed objects for an email
        WHEN the process_pending_enrollments signal handler is triggered
        THEN no LearningPathEnrollment objects are created
        """
        user = User.objects.create(email=self.user_email)

        process_pending_enrollments(sender=User, instance=user, created=True)

        enrollments = LearningPathEnrollment.objects.all()
        self.assertEqual(len(enrollments), 0)

    def test_process_pending_enrollments_when_not_created(self):
        """
        GIVEN that a user is updated
        WHEN the process_pending_enrollments signal handler is triggered with crated=False
        THEN no enrollment objects are created
        """
        user = User.objects.create(email=self.user_email)

        # Trigger the signal manually with created=False (user update)
        process_pending_enrollments(sender=User, instance=user, created=False)

        pending_entries = LearningPathEnrollmentAllowed.objects.all()
        self.assertEqual(len(pending_entries), 0)

        enrollments = LearningPathEnrollment.objects.all()
        self.assertEqual(len(enrollments), 0)
