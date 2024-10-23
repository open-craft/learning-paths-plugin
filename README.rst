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

    ```bash
    git clone <repository_url> <devstack_root>/src/learning-paths-plugin
    ```


2. **Install the Plugin**

    Inside the LMS shell, install the plugin by running:

    ```bash
    pip install -e /edx/src/learning-paths-plugin/
    ```

3. **Run Migrations for the Plugin**

    After installing the plugin, run the database migrations for `learning_paths`:

    ```bash
    ./manage.py lms migrate learning_paths
    ```

4. **Run Completion Aggregator Migrations**

    Ensure that the **completion aggregator** service is also up to date by running its migrations:

    ```bash
    ./manage.py lms migrate completion_aggregator
    ```

5. **Restart LMS**

    Restart the LMS to apply the changes:

Once these steps are complete, the Learning Paths plugin should be successfully installed and ready to use.
