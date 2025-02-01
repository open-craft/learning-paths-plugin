0003 Learning Path Enrollment API
#################################

Status
******

**Provisional**

.. Standard statuses
    - **Draft** if the decision is newly proposed and in active discussion
    - **Provisional** if the decision is still preliminary and in experimental phase
    - **Accepted** *(date)* once it is agreed upon
    - **Superseded** *(date)* with a reference to its replacement if a later ADR changes or reverses the decision

    If an ADR has Draft status and the PR is under review, you can either use the intended final status (e.g. Provisional, Accepted, etc.), or you can clarify both the current and intended status using something like the following: "Draft (=> Provisional)". Either of these options is especially useful if the merged status is not intended to be Accepted.

Context
*******

Learner enrollments in Learning Paths are captured in the LearningPathEnrollment
model. In this ADR, it is enhanced with necessary fields and API to perform
enrollments and store relevant data.

Decision
********

1. LearningPathEnrollment Model
===============================

Introduce new fields to the ``LearningPathEnrollment`` model:

#. ``is_active`` as a ``BooleanField`` that will indicate the enrolled/unenrolled
   state of the learner.
#. ``history`` as a `django-simple-history`_ ``HistoricalRecords`` field to
   preserve the record of changes made on an enrollment.
#. ``enrolled_at`` as a ``DateTimeField`` to record the timestamp of the
   enrollment. This will be explicitly set/reset when a user is enrolled in the
   Learning Path. It will hold the latest valid enrollment timestamp in case of
   un-enrollment and re-enrollment.

.. _django-simple-history: https://django-simple-history.readthedocs.io/en/latest/quick_start.html

2. ManualEnrollmentAudit Model
==============================

.. warning::

   The scope of this model is not finalized, so do not implement it yet.

Create a new Django model called ``ManualEnrollmentAudit`` to store metadata
about the Learning Path enrollments created manually.

**Reference:** LMS student course enrollment's `ManualEnrollmentAudit`_

Model attributes

* ``enrollment`` - ``ForeignKey`` field referencing ``LearningPathEnrollment``
* ``enrolled_by`` - ``ForeignKey`` field referencing the ``User`` performing the
  enrollment.
* ``role`` - ``CharField`` to store the role of the user creating the enrollment.
* ``enrolled_email`` - ``CharField`` to store the email of the learner.
* ``state_transition`` - ``CharField`` to store the enrollment state transition.
  This field will use the same values as `TRANSITION_STATES`_ from the LMS.
* ``reason`` - ``TextField`` to store reason for manual enrollment.
* ``history`` - `django-simple-history`_ ``HistoricalRecords`` field

.. _ManualEnrollmentAudit: https://github.com/openedx/edx-platform/blob/925716415c7794d3447acf575be241d767f5e07c/common/djangoapps/student/models/course_enrollment.py#L1514
.. _TRANSITION_STATES: https://github.com/openedx/edx-platform/blob/925716415c7794d3447acf575be241d767f5e07c/common/djangoapps/student/models/course_enrollment.py#L88

3. LearningPathEnrollmentAllowed Model
======================================

Create a new Django model called ``LearningPathEnrollmentAllowed`` to store
records of future enrollments to specific Learning Paths. The users may or may
not exist in the system yet.

**Reference:** LMS student course enrollment's `CourseEnrollmentAllowed`_.
Model

Model Attributes

* ``email`` - ``CharField`` to store the email of the user.
* ``learning_path`` - ``ForeignKey`` field to store the reference to the Learning
  Path.
* ``user`` - ``ForeignKey`` to the user who will be enrolled. Nullable to allow
  non-existing users to be referenced just with their email.

This model will be subclassed from the ``TimeStampedModel`` to include the
necessary timestamps.

.. _CourseEnrollmentAllowed: https://github.com/openedx/edx-platform/blob/925716415c7794d3447acf575be241d767f5e07c/common/djangoapps/student/models/course_enrollment.py#L1588


4. Enroll API
=============

Implement an API exposing the LearningPathEnrollment model. This API will allow
learners to be enrolled in the Learning Path.

+---------------------+-------------------------------------------------------+
| API Path            | /api/v1/learning-path-enrollment/<learning_path_id>   |
+---------------------+-------------------------------------------------------+
| Methods             | GET, POST, DELETE                                     |
+---------------------+-------------------------------------------------------+
| Query Params        | username (OPTIONAL)                                   |
+---------------------+-------------------------------------------------------+
| Permissions Required| LoggedIn                                              |
+---------------------+-------------------------------------------------------+

.. note::

   The ``learning_path_id`` will be changed to a human readable content key.


GET
"""

**Corresponding User Action:** Fetch enrollment in a Learning Path

* When the ``username`` query parameter is present, the api returns

  * the *active* enrollment object of the corresponding user for a **staff** user
    or when both ``currentUser`` and the ``username`` point to the same user.
  * HTTP 403 for a non-staff user, when ``currentUser`` and ``username``
    refer to different users.

* When the ``username`` query parameter is absent, the api returns

  * all the *active* enrollments in a Learning Path if the ``currentUser`` is a **staff**
    or **admin** user.
  * the ``LearningPathEnrollment`` object if the logged-in user is enrolled in the
    specified learning path. Otherwise returns a HTTP 404.


POST
""""

**Corresponding User Action:** Enroll

* When ``username`` is absent, enrolls the ``currentUser`` in the Learning
  Path reference by the ``learning_path_id``.
* When ``username`` is present

  * ``username`` is different from the ``currentUser``, the user
    linked to ``username`` will be enrolled, if the ``currentUser`` is a
    **staff** or **admin**.
  * Return an HTTP 403 error if the ``currentUser`` is a non-staff user
  * Return an HTTP 404 if the ``username`` or ``learning_path_id`` do not
    resolve into valid objects.

* When an *active* ``LearningPathEnrollment`` object exists for the user and the
  Learning Path, return HTTP 409 Conflict.


DELETE
""""""

**Corresponding User Action:** Unenroll

This will follow the same permission logic as the **POST** request allowing
both self-unenrollment and staff-unenrollment.

* Marks the *active* ``LearningPathEnrollment`` of the learner as inactive, by
  setting the ``is_active`` field to ``False`` when the learner has an active
  enrollment.
* Return a 404 when there are no active enrollments for the learner.

This method will be gated with a Django settings ``LEARNING_PATHS_ALLOW_SELF_UNENROLLMENT``
and will default to ``False`` and will have to be explicitly enabled.

* When the ``LEARNING_PATHS_ALLOW_SELF_UNENROLLMENT`` is ``False``, DELETE requests
  from non-staff members will be returned HTTP 403.


5. Fetch Enrollments API
========================

This API would list all the Learning Path enrollments

* of the user making the request, for a non-staff user
* of all users, for a staff user

+---------------------+-------------------------------------------------------+
| API Path            | /api/v1/enrollment/                                   |
+---------------------+-------------------------------------------------------+
| Methods             | GET                                                   |
+---------------------+-------------------------------------------------------+
| Permissions Required| LoggedIn                                              |
+---------------------+-------------------------------------------------------+

6. Bulk enrollment API
======================

In order for staff to bulk enroll users into learning paths, implement the
following API.

+---------------------+-------------------------------------------------------+
| API Path            | /api/v1/enrollment/bulk_enroll/                       |
+---------------------+-------------------------------------------------------+
| Methods             | POST                                                  |
+---------------------+-------------------------------------------------------+
| Permissions Required| Staff or Admin                                        |
+---------------------+-------------------------------------------------------+

The API will accept the following JSON data.

.. code::

   {
     "learning_paths": "path-v1:ABC+XYZ+2025_Term1,path-v1:CC+DDD+2025_Term1",
     "emails": "userA@example.com,new_user@example.com"
   }


* `learning_paths` - a comma separated list of the Learning Path keys to enroll
  learner into
* `emails` - a comma separated list of emails of the learners to enroll

The API view filter out the invalid emails and Learning Path IDs before
processing the enrollments. For all combination of valid Learning Paths and the
user emails, the following will be created:

#. A ``LearningPathEnrollmentAllowed`` object - with users linked for existing
   users, and just the emails for non-existing users.
#. A ``LearningPathEnrollment`` object for existing users.

.. note::

   The API currently is designed with minimal set of parameters to support
   enrollment of learners. It should be updated to include more fields in the
   future to accommodate extra metadata.


7. User model post_save signal receiver for auto enrollment
===========================================================

Since the bulk enrollment API supports enrolling non-existent users by creating
``LearningPathEnrollmentAllowed`` objects with just the email, there needs to be
a mechanism to automatically enroll the users when they register.

For course bulk enrollment, this is currently implemented in the
`user_post_save_callback`_ signal receiver.

By implementing a similar receiver in the learning-paths-plugin, learners who
have been enrolled into Learning Paths with their emails by the staff (i.e.,
with valid ``LearningPathEnrollmentAllowed`` objects), can be automatically
enrolled and their corresponding ``LearningPathEnrollment`` created.

.. _user_post_save_callback: https://github.com/openedx/edx-platform/blob/db0b5adc691f3e05d0b1bec2dba939d79a335270/common/djangoapps/student/models/user.py#L732


Consequences
************

* The Learning Path Enrollment APIs will allow existing users to self-enroll or
  staff to force enroll in Learning Paths.
* The Bulk Enrollment API will allow for staff to enroll a list of learners with
  or without an existing account to be enrolled into multiple Learning Paths in
  a single go.

Dealing with "invitation-only" courses
======================================

Access to courses can be restricted by marking them as "invitation-only". This
prevents learner from enrolling into courses without a staff member explicitly
inviting them.

If a Learning Path is composed of courses that are restricted using this flag,
either partially (some of the courses) or fully (all the courses), it creates
a scenario where a learner might be enrolled in a Learning Path using the
:ref:`Enroll API <4-enroll-api>`, but cannot enroll into a course that is a part
of the Learning Path.

This limitation will be addressed in a future ADR, that could possibly introduce
a flag on the ``LearningPath`` model allowing bypass of the "invitation-only"
restriction and allow the learners to enroll in such courses.

Rejected Alternatives
*********************

1. Enrollment eligibility checks in POST
========================================

Implement an ``canEnroll`` check for a Learning Path that can determine if a
learner is eligible to enroll in all of the underlying courses before
creating an enrollment.

While this will solve the issues where an user is enrolled in a Learning Path,
but lacks access to the underlying courses at the time of enrollment, it is
flawed in other scenarios like:

* courses in a learning path are gated by prerequisites like skills or
  completion of other courses
* courses are marked as "invite only" but are available via their enterprise's
  catalog ...etc.,
* course is open during the time of Learning Path enrollment, but closes
  before the learner completes preceding courses.
