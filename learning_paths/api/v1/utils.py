"""
Util methods for LearningPath
"""

from typing import Any

from django.conf import settings
from opaque_keys.edx.keys import CourseKey

try:
    from openedx.core.djangoapps.catalog.utils import get_catalog_api_client
    from lms.djangoapps.grades.course_grade_factory import CourseGradeFactory
except ImportError:
    pass
from requests.exceptions import HTTPError
from rest_framework.exceptions import APIException

from ...models import LearningPathStep, LearningPathGradingCriteria


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
            raise APIException(
                f"Error fetching completion for course {course_id}: {err}"
            ) from err

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
        course_completion = get_course_completion(
            user.username, step.course_key, client
        )
        total_completion += course_completion

    total_courses = len(steps)

    if total_courses == 0:
        return 0.0

    aggregate_progress = total_completion / total_courses
    return aggregate_progress


def is_learning_path_completed(user, learning_path):
    """
    Check if the user has completed the learning path.
    Completion is determined if the aggregate progress meets or exceeds the completion threshold.
    """
    try:
        grading_criteria = LearningPathGradingCriteria.objects.get(
            learning_path=learning_path
        )
    except LearningPathGradingCriteria.DoesNotExist:
        return False

    aggregate_progress = get_aggregate_progress(user, learning_path)
    return aggregate_progress >= grading_criteria.completion_threshold


def get_user_course_grade(user, course_key_str):
    """
    Retrieve the CourseGrade object for a user in a specific course.
    """
    course_key = CourseKey.from_string(course_key_str)
    course_grade = CourseGradeFactory().read(user, course_key)
    return course_grade


def calculate_learning_path_grade(user, learning_path):
    """
    Calculate the aggregate grade for a user across a learning path based on weighted course grades.
    Only calculate if the learning path is completed.
    """
    if not is_learning_path_completed(user, learning_path):
        return 0.0

    total_weight = 0.0
    weighted_sum = 0.0

    for step in learning_path.steps.all():
        course_grade = get_user_course_grade(user, step.course_key)
        course_weight = step.weight
        weighted_sum += course_grade.percent * course_weight
        total_weight += course_weight

    # Calculate the weighted average grade
    return (weighted_sum / total_weight) * 100 if total_weight > 0 else 0.0
