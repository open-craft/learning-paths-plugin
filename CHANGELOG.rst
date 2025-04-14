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
