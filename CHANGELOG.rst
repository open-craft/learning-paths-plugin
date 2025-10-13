Change Log
##########

..
   All enhancements and patches to learning_paths will be documented
   in this file.  It adheres to the structure of https://keepachangelog.com/ ,
   but in reStructuredText instead of Markdown (for ease of incorporation into
   Sphinx documentation and the PyPI description).

   This project adheres to Semantic Versioning (https://semver.org/).

.. There should always be an "Unreleased" section for changes pending release.

Unreleased
**********

*

0.3.5 - 2025-09-01
******************

Changed
=======

* Allow changing the Learning Path key in the Django admin interface.

Removed
=======

* Grading criteria from the Django admin interface.
* Step weight and order from the Django admin interface.

0.3.4 - 2025-08-02
******************

Added
=====

* Bulk unenrollment API.
* Enrollment audit model that tracks the enrollment state transitions.
* Allow specifying time commitment.
* Allow duplicating Learning Paths in the Django admin interface.

Changed
=======

* The Learning Paths API includes start and end dates for its steps.
* Return enrollment date in the API instead of a boolean.
* Allow specifying any text for the duration.
* Make the skill level optional.

0.3.3 - 2025-05-23
******************

Changed
=======

* Changed line length from 80 to 120 characters.

0.3.2 - 2025-05-02
******************

Added
=====

* Course key selection in admin forms.
* Learning Path selection field in admin forms.
* Enrollment status to the Learning Path list and retrieve APIs.
* Invite-only functionality for Learning Paths.
* Course enrollment API.

Changed
=======

* The Learning Path ``subtitle`` to ``TextField`` and made it optional.
* The image URL field to ``ImageField``.
* The user field on the admin enrollments page to raw ID, to prevent the page
  from retrieving all users in the system.

Removed
=======

* The ``slug`` field from the Learning Path model.
* The UUID compatibility layer from Learning Path keys.

0.3.1 - 2025-04-14
******************

Added
=====

* API for listing and retrieving Learning Paths.

Fixed
=====

* Automatically create grading criteria for Learning Paths.

Changed
=======

* Replaced relative due dates with actual due dates from course runs.

0.3.0 - 2025-04-03
******************

Changed
=======

* Replaced Learning Path UUID with LearningPathKey.

0.2.3 - 2025-03-31
******************

Added
=====

* Enrollment API.

0.2.2 - 2024-12-05
******************

Added
=====

* User grade API

0.2.1 - 2024-10-28
******************

Added
=====

* Progress API

0.2.0 - 2024-01-23
******************

Added
=====

* Database models
* Django Admin interface
