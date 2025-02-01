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

We will create a new view in the `api` app to expose an API that can be called
by other services to enroll a learner in the Learning Path.

+---------------------+-------------------------------------------------------+
| API Path            | /api/v1/learning-path/<uuid:learning-path-id>/enroll/ |
+---------------------+-------------------------------------------------------+
| Method              | POST                                                  |
+---------------------+-------------------------------------------------------+
| Data                | username                                              |
+---------------------+-------------------------------------------------------+
| Permissions Required| LoggedIn                                              |
+---------------------+-------------------------------------------------------+

.. note:: The UUID in the URL will be replaced with a more human friendly key
   later.


Consequences
************

* The new API will allow external services with valid user credentials (eg.,
  MFEs) to enroll learners in Learning Paths.
* While access to courses can be restricted by marking them "Invitation
  Required", there is no such flag for a Learning Path. So, any learner who
  knows the ID of a Learning Path can enroll in it, without actaully having
  access to any of the courses in the Learning Path. This shortcoming will have
  be addressed in future development.

Rejected Alternatives
*********************

NA
