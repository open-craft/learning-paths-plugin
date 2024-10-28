learning-paths-plugin
#####################

Purpose
*******

A Learning Path consists of a selection of courses bundled together for
learners to progress through. This plugin enables the creation and
management of Learning Paths.

License
*******

The code in this repository is licensed under the Not open source unless
otherwise noted.

Please see `LICENSE.txt <LICENSE.txt>`_ for details.

Installation and Configuration
******************************

1. **Clone the Repository**

   Clone the repository containing the plugin to the `src` directory under your devstack root:

   .. code-block:: bash

      git clone <repository_url> <devstack_root>/src/learning-paths-plugin

2. **Install the Plugin**

   Inside the LMS shell, install the plugin by running:

   .. code-block:: bash

      pip install -e /edx/src/learning-paths-plugin/

3. **Run Migrations for the Plugin**

   After installing the plugin, run the database migrations for `learning_paths`:

   .. code-block:: bash

      ./manage.py lms migrate learning_paths

4. **Run Completion Aggregator Migrations**

   Ensure that the **completion aggregator** service is also up to date by running its migrations:

   .. code-block:: bash

      ./manage.py lms migrate completion_aggregator

   .. warning::

      Please read the section about `synchronous vs asynchronous modes <https://github.com/open-craft/openedx-completion-aggregator/?tab=readme-ov-file#synchronous-vs-asynchronous-calculations>`_
      for completion aggregator before enabling this in a production environment. Running in synchronous mode can lead to an outage.


Once these steps are complete, the Learning Paths plugin should be successfully installed and ready to use.


Usage
*****
After installing the plugin, a learning path can be created in the django admin panel `{LMS_URL}/admin/learning_paths/learningpath/`.
