"""
learning_paths Django application initialization.
"""

from django.apps import AppConfig
from edx_django_utils.plugins.constants import PluginSettings, PluginSignals, PluginURLs


class LearningPathsConfig(AppConfig):
    """
    Configuration for the learning_paths Django application.
    """

    name = "learning_paths"
    verbose_name = "Learning Paths"

    plugin_app = {
        # Configuration setting for Plugin URLs for this app.
        PluginURLs.CONFIG: {
            "lms.djangoapp": {
                # The namespace to provide to django's urls.include.
                PluginURLs.NAMESPACE: "learning_paths",
                # The application namespace to provide to django's urls.include.
                # Optional; Defaults to None.
                PluginURLs.APP_NAME: "learning_paths",
                # The regex to provide to django's urls.url.
                # Optional; Defaults to r''.
                # PluginURLs.REGEX: r'^api/learning_paths/',
                # The python path (relative to this app) to the URLs module to be plugged into the project.
                # Optional; Defaults to 'urls'.
                # PluginURLs.RELATIVE_PATH: 'api.urls',
            }
        },
        PluginSettings.CONFIG: {
            "lms.djangoapp": {
                "common": {
                    PluginSettings.RELATIVE_PATH: "settings",
                }
            }
        },
        PluginSignals.CONFIG: {
            "lms.djangoapp": {
                PluginSignals.RELATIVE_PATH: "receivers",
                PluginSignals.RECEIVERS: [
                    {
                        PluginSignals.RECEIVER_FUNC_NAME: "process_pending_enrollments",
                        PluginSignals.SIGNAL_PATH: "django.db.models.signals.post_save",
                        PluginSignals.SENDER_PATH: "django.contrib.auth.models.User",
                    }
                ],
            }
        },
    }
