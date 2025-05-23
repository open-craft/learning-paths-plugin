"""
Util methods for LearningPath
"""

from typing import Any

from django.conf import settings
from opaque_keys.edx.keys import CourseKey
from requests.exceptions import HTTPError
from rest_framework.exceptions import APIException

from ...compat import get_catalog_api_client
from ...models import LearningPathStep


def get_course_completion(username: str, course_key: CourseKey, client: Any) -> float:
    """
    Fetch the completion percentage of a course for a specific user via an internal API request.
    """
    course_id = str(course_key)
    lms_base_url = settings.LMS_ROOT_URL
    completion_url = f"{lms_base_url}/completion-aggregator/v1/course/{course_id}/?username={username}"

    try:
        response = client.get(completion_url)
        response.raise_for_status()
        data = response.json()
    except HTTPError as err:
        if err.response.status_code == 404:
            return 0.0
        else:
            raise APIException(f"Error fetching completion for course {course_id}: {err}") from err

    if data and data.get("results"):
        return data["results"][0]["completion"]["percent"]
    return 0.0


def get_aggregate_progress(user, learning_path):
    """
    Calculate the aggregate progress for all courses in the learning path.
    """
    steps = LearningPathStep.objects.filter(learning_path=learning_path)

    client = get_catalog_api_client(user)
    # TODO: Create a native Python API in the completion aggregator
    # to avoid the overhead of making HTTP requests and improve performance.

    total_completion = 0.0

    for step in steps:
        course_completion = get_course_completion(user.username, step.course_key, client)
        total_completion += course_completion

    total_courses = len(steps)

    if total_courses == 0:
        return 0.0

    aggregate_progress = total_completion / total_courses
    return aggregate_progress
