# pylint: disable=redefined-outer-name
"""Tests for the signals module."""

import pytest
from django.contrib.auth import get_user_model

from learning_paths.models import (
    LearningPathEnrollment,
    LearningPathEnrollmentAllowed,
    LearningPathEnrollmentAudit,
)
from learning_paths.receivers import process_pending_enrollments

from .factories import (
    LearningPathEnrollmentAllowedFactory,
    LearningPathEnrollmentFactory,
    LearningPathFactory,
    UserFactory,
)

User = get_user_model()


@pytest.fixture
def user_email():
    """Return a test email address."""
    return "test@example.com"


@pytest.fixture
def learning_paths():
    """Create two learning paths for testing."""
    return [LearningPathFactory(), LearningPathFactory()]


@pytest.mark.django_db
def test_process_pending_enrollments_with_pending_enrollments(user_email, learning_paths):
    """
    GIVEN that there are LearningPathEnrollmentAllowed objects for an email
    WHEN the process_pending_enrollments signal handler is triggered
    THEN actual enrollment objects are created for the user
    AND audit records are created for the new enrollments
    AND audit data is preserved from the last "allowed to enroll" audit
    AND existing audits are linked to the new enrollment
    AND enrollment allowed records are deactivated and linked to the user
    """
    initial_audit_payload = {"role": "TestRole"}
    pending_entry_1 = LearningPathEnrollmentAllowedFactory(
        email=user_email, learning_path=learning_paths[0], _audit=initial_audit_payload
    )
    pending_entry_2 = LearningPathEnrollmentAllowedFactory(email=user_email, learning_path=learning_paths[1])
    pending_entry_2.audit.all().delete()  # Test that the enrollment can be created without an allowed audit.

    user = UserFactory(email=user_email)
    process_pending_enrollments(sender=User, instance=user, created=True)

    pending_entry_1.refresh_from_db()
    pending_entry_2.refresh_from_db()
    assert pending_entry_1.user == user
    assert pending_entry_2.user == user
    assert pending_entry_1.is_active is False
    assert pending_entry_2.is_active is False

    enrollments = LearningPathEnrollment.objects.all()
    assert len(enrollments) == 2
    assert all(e.user == user for e in enrollments)
    assert enrollments[0].learning_path == pending_entry_1.learning_path
    assert enrollments[1].learning_path == pending_entry_2.learning_path

    assert LearningPathEnrollmentAudit.objects.count() == 3
    for enrollment in enrollments:
        audit = enrollment.audit.last()
        assert audit.state_transition == LearningPathEnrollmentAudit.ALLOWEDTOENROLL_TO_ENROLLED
        assert audit.enrolled_by == user
        assert audit.reason == ""
        assert audit.org == ""

    assert enrollments[0].audit.count() == 2
    assert enrollments[0].audit.first().enrollment_allowed == pending_entry_1
    assert enrollments[0].audit.last().role == initial_audit_payload["role"]

    assert enrollments[1].audit.count() == 1
    assert enrollments[1].audit.get().role == ""


@pytest.mark.django_db
def test_process_pending_enrollments_only_processes_active_records(user_email, learning_paths):
    """
    GIVEN that there are both active and inactive LearningPathEnrollmentAllowed objects for an email
    WHEN the process_pending_enrollments signal handler is triggered
    THEN only active enrollment allowed records are processed
    """
    active_entry = LearningPathEnrollmentAllowedFactory(
        email=user_email, learning_path=learning_paths[0], is_active=True
    )
    inactive_entry = LearningPathEnrollmentAllowedFactory(
        email=user_email, learning_path=learning_paths[1], is_active=False
    )

    user = UserFactory(email=user_email)
    process_pending_enrollments(sender=User, instance=user, created=True)

    enrollments = LearningPathEnrollment.objects.all()
    assert len(enrollments) == 1
    assert enrollments[0].learning_path == active_entry.learning_path

    active_entry.refresh_from_db()
    assert active_entry.is_active is False
    assert active_entry.user == user

    inactive_entry.refresh_from_db()
    assert inactive_entry.is_active is False
    assert inactive_entry.user is None


@pytest.mark.django_db
def test_process_pending_enrollments_when_no_pending_enrollments(user_email):
    """
    GIVEN that there are no LearningPathEnrollmentAllowed objects for an email
    WHEN the process_pending_enrollments signal handler is triggered
    THEN no LearningPathEnrollment objects are created
    """
    user = UserFactory(email=user_email)
    process_pending_enrollments(sender=User, instance=user, created=True)

    enrollments = LearningPathEnrollment.objects.all()
    assert len(enrollments) == 0


@pytest.mark.django_db
def test_process_pending_enrollments_when_not_created(user_email):
    """
    GIVEN that a user is updated
    WHEN the process_pending_enrollments signal handler is triggered with created=False
    THEN no enrollment objects are created
    """
    user = UserFactory(email=user_email)

    # Trigger the signal manually with created=False (user update)
    process_pending_enrollments(sender=User, instance=user, created=False)

    pending_entries = LearningPathEnrollmentAllowed.objects.all()
    assert len(pending_entries) == 0

    enrollments = LearningPathEnrollment.objects.all()
    assert len(enrollments) == 0


# pylint: disable=protected-access
@pytest.mark.django_db
class TestEnrollmentAuditReceivers:
    """Tests for the audit record creation signals."""

    @pytest.mark.parametrize(
        "expected_state,expected_values",
        [
            (
                LearningPathEnrollmentAudit.UNENROLLED_TO_ENROLLED,
                {"enrolled_by": "user", "reason": "TestReason", "org": "TestOrg", "role": "Tester"},
            ),
            (
                LearningPathEnrollmentAudit.UNENROLLED_TO_ENROLLED,
                {"enrolled_by": None, "reason": "", "org": "", "role": ""},
            ),
        ],
        ids=["with_audit_data", "without_audit_data"],
    )
    def test_create_enrollment_audit_new_enrollment(self, user, learning_path, expected_state, expected_values):
        """Test audit creation for a new enrollment with or without explicit audit data."""
        if expected_values["reason"]:
            expected_values["enrolled_by"] = user
            enrollment = LearningPathEnrollmentFactory.create(
                user=user, learning_path=learning_path, _audit=expected_values
            )
        else:
            enrollment = LearningPathEnrollmentFactory.create(user=user, learning_path=learning_path)

        audit = enrollment.audit.get()
        assert audit.state_transition == expected_state
        for field, value in expected_values.items():
            assert getattr(audit, field) == value

    @pytest.mark.parametrize(
        "initial_state,new_state,expected_transition,audit_data",
        [
            (False, True, LearningPathEnrollmentAudit.UNENROLLED_TO_ENROLLED, {"reason": "Reactivation"}),
            (True, False, LearningPathEnrollmentAudit.ENROLLED_TO_UNENROLLED, {"reason": "Deactivation"}),
            (True, True, LearningPathEnrollmentAudit.ENROLLED_TO_ENROLLED, {"reason": "Updated reason"}),
            (False, False, LearningPathEnrollmentAudit.UNENROLLED_TO_UNENROLLED, {"reason": "Still inactive"}),
        ],
        ids=["reactivate", "deactivate", "no_state_change_active", "no_state_change_inactive"],
    )
    def test_create_enrollment_audit_state_changes(  # pylint: disable=too-many-positional-arguments
        self, user, learning_path, initial_state, new_state, expected_transition, audit_data
    ):
        """Test audit creation when the enrollment state changes."""
        enrollment = LearningPathEnrollmentFactory.create(
            user=user, learning_path=learning_path, is_active=initial_state
        )

        enrollment.is_active = new_state
        enrollment._audit = {"enrolled_by": user, **audit_data}
        enrollment.save()

        assert enrollment.audit.count() == 2
        audit = enrollment.audit.last()
        assert audit.state_transition == expected_transition
        assert audit.enrolled_by == user
        assert audit.reason == audit_data["reason"]

    @pytest.mark.parametrize(
        "updated_audit,expected_values",
        [
            (
                {},
                {"reason": "TestReason", "org": "TestOrg", "role": "TestRole"},
            ),
            (
                {"reason": "", "org": "", "role": ""},
                {"reason": "TestReason", "org": "TestOrg", "role": "TestRole"},
            ),
            (
                {"reason": "New Reason", "org": "New Org", "role": "New Role"},
                {"reason": "New Reason", "org": "New Org", "role": "New Role"},
            ),
        ],
        ids=["preserve_metadata", "preserve_over_empty_strings", "use_provided_metadata"],
    )
    def test_create_enrollment_audit_metadata_handling(self, user, learning_path, updated_audit, expected_values):
        """Test how metadata is preserved or updated in audit records."""
        initial_audit_payload = {"enrolled_by": user, "reason": "TestReason", "org": "TestOrg", "role": "TestRole"}
        enrollment = LearningPathEnrollmentFactory.create(
            user=user, learning_path=learning_path, _audit=initial_audit_payload
        )

        another_user = UserFactory()
        enrollment.is_active = False
        enrollment._audit = {"enrolled_by": another_user, **updated_audit}
        enrollment.save()

        assert enrollment.audit.count() == 2
        latest_audit = enrollment.audit.last()

        assert latest_audit.state_transition == LearningPathEnrollmentAudit.ENROLLED_TO_UNENROLLED
        assert latest_audit.enrolled_by == another_user
        for field, value in expected_values.items():
            assert getattr(latest_audit, field) == value

    def test_create_enrollment_allowed_audit_with_audit_data(self, user, learning_path):
        """Test audit creation for a new LearningPathEnrollmentAllowed with explicit audit data."""
        audit_payload = {"enrolled_by": user, "reason": "TestReason", "org": "TestOrg", "role": "TestRole"}
        enrollment_allowed = LearningPathEnrollmentAllowedFactory.create(
            email="testallow@example.com", learning_path=learning_path, _audit=audit_payload
        )
        audit = enrollment_allowed.audit.get()
        assert audit.state_transition == LearningPathEnrollmentAudit.UNENROLLED_TO_ALLOWEDTOENROLL
        for field, value in audit_payload.items():
            assert getattr(audit, field) == value

    def test_create_enrollment_allowed_audit_without_audit_data_is_skipped(self, learning_path, user_email):
        """Test that no audit is created for LearningPathEnrollmentAllowed if _audit is not present."""
        enrollment_allowed = LearningPathEnrollmentAllowedFactory.create(email=user_email, learning_path=learning_path)
        assert not enrollment_allowed.audit.exists()

    def test_create_enrollment_allowed_audit_metadata_handling(self, user, learning_path, user_email):
        """Test that LearningPathEnrollmentAllowed audit records handle metadata correctly."""
        initial_payload = {"enrolled_by": user, "reason": "TestReason", "org": "TestOrg"}
        enrollment_allowed = LearningPathEnrollmentAllowedFactory.create(
            email=user_email, learning_path=learning_path, _audit=initial_payload
        )

        another_user = UserFactory()
        enrollment_allowed._audit = {"enrolled_by": another_user, "reason": "", "role": "TestRole"}
        enrollment_allowed.save()

        assert enrollment_allowed.audit.count() == 2
        latest_audit = enrollment_allowed.audit.last()

        assert latest_audit.enrolled_by == another_user
        assert latest_audit.reason == initial_payload["reason"]
        assert latest_audit.org == initial_payload["org"]
        assert latest_audit.role == "TestRole"
        assert latest_audit.state_transition == LearningPathEnrollmentAudit.UNENROLLED_TO_ALLOWEDTOENROLL
