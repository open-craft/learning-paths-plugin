from django.conf import settings
from opaque_keys.edx.keys import CourseKey
from openedx.core.djangoapps.catalog.utils import get_catalog_api_client
from rest_framework.exceptions import APIException
from ...models import LearningPathStep
from requests.exceptions import HTTPError
from typing import Any


def get_course_completion(username: str, course_key: CourseKey, client: Any) -> float:
    """
    Fetch the completion percentage of a course for a specific user via an internal API request.
    """
    course_id = str(course_key)
    lms_base_url = settings.LMS_ROOT_URL
    username = username
    completion_url = f"{lms_base_url}/completion-aggregator/v1/course/{course_id}/?username={username}"

    try:
        response = client.get(completion_url)
        response.raise_for_status()
        data = response.json()
    except HTTPError as err:
        if err.response.status_code == 404:
            return 0.0
        else:
            raise APIException(f"Error fetching completion for course {course_id}: {err}")

    if data and data.get("results"):
        return data["results"][0]["completion"]["percent"]
    return 0.0


def get_aggregate_progress(request, learning_path):
    """
    Calculate the aggregate progress for all courses in the learning path.
    """
    steps = LearningPathStep.objects.filter(learning_path=learning_path)

    if total_courses == 0:
        return 0.0

    client = get_catalog_api_client(request.user)
    # TODO: Create a native Python API in the completion aggregator
    # to avoid the overhead of making HTTP requests and improve performance.

    total_completion = 0.0

    for step in steps:
        course_completion = get_course_completion(request.user.username, step.course_key, client)
        total_completion += course_completion

    total_courses = len(steps)

    aggregate_progress = total_completion / total_courses
    return aggregate_progress
