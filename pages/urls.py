from django.urls import path
from . import views

urlpatterns = [
    path("main/", views.HomePageView.as_view(), name="home"),
    path("main/tasks/<task_id>/", views.get_status, name="get_status"),
    path("main/tasks/", views.run_task, name="run_task"),
]
