0001 Purpose of This Repo
#########################

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

Organizations want to offer courses in bundles that learners can sign
up for once and progress through. The aim of a Learning Path is for learners to
master a particular subject or skill.

Decision
********

We will create an Open edX Django plugin that implements the necessary
functionality. This plugin will provide the necessary data models and
interface for the admins to create and manage the Learning Paths and related
actions like enrollments and credentials.

In the initial implementation, we will use the Programs feature of the
`course discovery`_ as the final data store and sync the data from the
learning-paths-plugin to course-discovery. This provides a quick way to
include the Learning Paths in other places like the `enterprise catalog`_.

Consequences
************

* The plugin provides a starting point for organizations to pack courses in
  new ways not supported natively by the edx-platform.

* By implementing the features as a plugin, the deployments are made easier.

* We will have to implement a way to sync the data from learning-paths-plugin
  to the course-discovery, which might introduce changes to the
  course-discovery service.

Rejected Alternatives
*********************

We considered using the edX Programs feature, however the edX enterprise
stack is very complex and very specific to edx.org's business requirements,
presenting numerous challenges in deployment and customisation.

References
**********

.. _course discovery: https://github.com/openedx/course-discovery/
.. _enterprise catalog: https://github.com/openedx/enterprise-catalog/
