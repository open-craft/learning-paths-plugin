0002 Initial Database Models
############################

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

We would like, initially, that a user could perform CRUD operations on
Learning Paths via the Django Admin. For that we must define data models.

Decision
********

We will define the following database models and their relationships:

* LearningPath

  - represents a Learning Path
  - identified by a unique user-defined `key`
  - contains multiple `LearningPathStep` children

* LearningPathStep

  - represents a course in a Learning Path
  - refers to course by a `CourseKeyField` from edx-opaque-keys
  - has an `order` integer field to allow ordering within the Learning Path
  - can require multiple `Skill`'s at specified levels
  - can have multiple `Skill`'s as acquired skills at specified levels

* Skill

  - represents a skill that courses in a Learning Path may require or teach

* RequiredSkill

  - represents a `Skill` at a specified level as a requirement of a
    `LearningPathStep`

* AcquiredSkill

  - represents a `Skill` at a specified level acquired through a
    `LearningPathStep`

Consequences
************

It is likely that new precise requirements will be identified in later
development which will bring the need for changes to these models and
corresponding database migrations, but these models will provide a starting
point.

Rejected Alternatives
*********************

Having a foreign key to `CourseOverview` from edx-platform as the reference
to course in `LearningPathStep`, instead of an opaque key, introduces a
dependency on edx-platform. Should it be necessary to use this foreign key,
e.g. to allow selecting courses in Django Admin or to take advantage of
database foreign key constraint enforcement, migration should be easy.
