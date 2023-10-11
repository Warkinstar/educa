from pages.tasks import create_task
from unittest.mock import patch
from django.test import TestCase
from django.shortcuts import reverse
import json


def test_task():
    """we used the .run method (rather than .delay) to run the task directly without a Celery worker."""
    assert create_task.run(1)
    assert create_task.run(2)
    assert create_task.run(3)


@patch("pages.tasks.create_task.run")
def test_mock_task(mock_run):
    """код @patch("tasks.sample_tasks.create_task.run") указывает, что метод create_task.run из
    модуля tasks.sample_tasks будет заменен фиктивной версией во время выполнения теста. Это делается с целью ускорения
    выполнения тестов, так как задачи будут выполняться внутри теста без задержки, которую обычно вызывает выполнение
    задачи через Celery"""
    assert create_task.run(1)
    create_task.run.assert_called_once_with(1)

    assert create_task.run(2)
    assert create_task.run.call_count == 2

    assert create_task.run(3)
    assert create_task.run.call_count == 3


class CreateTaskTests(TestCase):
    def test_task_status(self):
        response = self.client.post(reverse("run_task"), {"type": 0}, secure=True)
        content = json.loads(response.content)
        task_id = content["task_id"]
        assert response.status_code == 202
        assert task_id

        response = self.client.get(reverse("get_status", args=[task_id]), secure=True)
        content = json.loads(response.content)
        assert content == {
            "task_id": task_id,
            "task_status": "PENDING",
            "task_result": None,
        }
        assert response.status_code == 200

        while content["task_status"] == "PENDING":
            response = self.client.get(reverse("get_status", args=[task_id]), secure=True)
            content = json.loads(response.content)
        assert content == {
            "task_id": task_id,
            "task_status": "SUCCESS",
            "task_result": True,
        }
