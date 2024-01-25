""" API v1 URLs. """

from rest_framework import routers

from learning_paths.api.v1.views import LearningPathAsProgramViewSet

router = routers.SimpleRouter()
router.register(
    r"programs", LearningPathAsProgramViewSet, basename="learning-path-as-program"
)

urlpatterns = router.urls
