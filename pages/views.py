from django.shortcuts import render
from django.views.generic.base import TemplateView
from django.views.decorators.csrf import csrf_exempt
from pages.tasks import create_task
from celery.result import AsyncResult
from django.http import JsonResponse


class HomePageView(TemplateView):
    template_name = "pages/main.html"

@csrf_exempt
def run_task(request):
    """For test celery, make celery task"""
    if request.POST:
        task_type = request.POST.get("type")
        task = create_task.delay(int(task_type))
        return JsonResponse({"task_id": task.id}, status=202)


@csrf_exempt
def get_status(request, task_id):
    """For test celery, return task status"""
    task_result = AsyncResult(task_id)
    result = {
        "task_id": task_id,
        "task_status": task_result.status,
        "task_result": task_result.result,
    }
    return JsonResponse(result, status=200)