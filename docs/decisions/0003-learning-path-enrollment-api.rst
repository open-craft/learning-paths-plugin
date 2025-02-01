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

We will create the following views in the ``api`` app to expose an API that can be called
by other services and MFEs.

.. _enroll-api:

1. Enroll API
=============

This API will allow learners to be enrolled in the

+---------------------+-------------------------------------------------------+
| API Path            | /api/v1/learning-path-enrollment/                     |
+---------------------+-------------------------------------------------------+
| Methods             | GET, POST, DELETE                                     |
+---------------------+-------------------------------------------------------+
| Data                | learning_path_id (uuid), username (OPTIONAL)          |
+---------------------+-------------------------------------------------------+
| Permissions Required| LoggedIn                                              |
+---------------------+-------------------------------------------------------+

.. note:: The UUID of the learning_path_id will be replaced with a more
   user-friendly value later.

GET
"""

**Corresponding User Action:** Fetch my enrollment

* The data fields ``learning_path_id`` and ``username`` will be passed as query
  parameters.
* Return the LearningPathEnrollment object if the logged-in user is enrolled in the
  specified learning path. Otherwise returns a HTTP 404.
* When the ``username`` is present, returns all the enrollments in a learning
  path if the ``currentUser`` is a **staff** or **admin** user.


POST
""""

**Corresponding User Action:** Enroll

* When ``username`` is absent, enrolls the ``currentUser`` in the Learning
  Path reference by the ``learning_path_id``.
* When ``username`` is passed and is different from the ``currentUser``, the user
  linked to ``username`` will be enrolled, if the ``currentUser`` is a **staff**
  or **admin**.
* For non-admin or non-staff users, when the ``currentUser`` and the user linked
  to ``username`` are different, return a HTTP 403.

DELETE
""""""

**Corresponding User Action:** Unenroll

This will follow the same permission logic as the **POST** request allowing
both self-unenrollment and staff-unenrollment.


2. LearningPathEnrollment Model
===============================

Add a new ``enrolled_by`` as a ``ForeignKey`` field to the
``LearningPathEnrollment`` model that will store the user who created the
enrollment. This will allow for distinguishing between self and staff
enrollments.

Since it is already a subclass of the ``TimeStatmpedModel``, we don't need to
introduce a ``enrolled_at`` field and can instead depend on the inherited ``created``
field.

Consequences
************

* The new API will allow external services with valid user credentials (eg.,
  MFEs) to enroll learners in Learning Paths.
* While access to courses can be restricted by marking them "Invitation
  Required", there is no such flag for a Learning Path. So, any learner who
  knows the ID of a Learning Path can enroll using the :ref:`Enroll API <enroll-api>`,
  without actaully having access to any of the courses in the Learning Path. This
  shortcoming will have be addressed in future development.

Rejected Alternatives
*********************

1. Enrollment eligibility checks in POST
========================================

Implement an ``canEnroll`` check for a LearningPath that can determine if a
learner is eligible to enroll in all of the underlying courses before
creating an enrollment.

While this will solve the issues where an user is enrolled in a Learning Path,
but lacks access to the underlying courses at the time of enrollment, it is
flawed in other scenarios like:
* courses in a learning path are gated by pre-requisites like skills or
  completion of other courses
* courses are marked as "invite only" but are available via their enterprise's
  catalog ...etc.,
