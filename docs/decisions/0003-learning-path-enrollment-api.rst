0003 Learning Path Enrollment API
###########################################

Status
******

**Draft**

.. Standard statuses
    - **Draft** if the decision is newly proposed and in active discussion
    - **Provisional** if the decision is still preliminary and in experimental phase
    - **Accepted** *(date)* once it is agreed upon
    - **Superseded** *(date)* with a reference to its replacement if a later ADR changes or reverses the decision

    If an ADR has Draft status and the PR is under review, you can either use the intended final status (e.g. Provisional, Accepted, etc.), or you can clarify both the current and intended status using something like the following: "Draft (=> Provisional)". Either of these options is especially useful if the merged status is not intended to be Accepted.

Context
*******

Learner enrollments in Learning Paths are captured in the
LearningPathEnrollment model. However, there is no API exposing an interface to
perform operations on the model.

Decision
********

We will create the following views in the ``api`` package to expose an API that can be called
by other services and MFEs.

.. _enroll-api:

1. Enroll API
=============

This API will allow learners to be enrolled in the Learning Path.

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
   The UUID of the learning_path_id will be replaced with a more
   user-friendly value later.

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
and ``LEARNING_PATHS_ALLOW_STAFF_UNENROLLMENT`` that will default to ``False`` and
will have to be explicitly enabled.

* When the ``LEARNING_PATHS_ALLOW_STAFF_UNENROLLMENT`` is ``False``, the ``is_active``
  field will be marked as **read-only**, preventing staff from unenrolling learners.
* When the ``LEARNING_PATHS_ALLOW_SELF_UNENROLLMENT`` is ``False``, DELETE requests
  from non-staff members will be returned HTTP 403.


2. Fetch Enrollments API
========================

This API would list all the Learning Path enrollments

* of the user making the request, for a non-staff user
* of all users, for a staff user

+---------------------+-------------------------------------------------------+
| API Path            | /api/v1/learning-path-enrollment/                     |
+---------------------+-------------------------------------------------------+
| Methods             | GET                                                   |
+---------------------+-------------------------------------------------------+
| Permissions Required| LoggedIn                                              |
+---------------------+-------------------------------------------------------+


3. LearningPathEnrollment Model
===============================

Introduce new fields to the ``LearningPathEnrollment`` model:

#. ``is_active`` as a ``BooleanField`` that will indicate the enrolled/unenrolled
   state of the learner.
#. ``history`` as a `django-simple-history`_ ``HistoricalRecords`` field to preserve
   the record of changes made on an enrollment.

.. note::

   Since it is already a subclass of the ``TimeStatmpedModel``, we don't need to
   introduce a ``enrolled_at`` field and can instead depend on the inherited ``created``
   field.


.. _django-simple-history: https://django-simple-history.readthedocs.io/en/latest/quick_start.html

Consequences
************

* The new API will allow external services with valid user credentials (eg.,
  MFEs) to enroll learners in Learning Paths.

Dealing with "invitation-only" courses
======================================

Access to courses can be restricted by marking them as "invitation-only". This
prevents learner from enrolling into courses without a staff member explicitly
inviting them.

If a Learning Path is composed of courses that are restricted using this flag,
either partially (some of the courses) or fully (all the courses), it creates
a scenario where a learner might be enrolled in a Learning Path using the
:ref:`Enroll API <enroll-api>`, but cannot enroll into a course that is a part
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
