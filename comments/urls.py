from django.urls import path
from . import views

app_name = 'comments'

urlpatterns = [
    path('module/<uuid:module_public_id>/', views.module_comments_list, name='module_comments_list'),
    path('module/<uuid:module_public_id>/add/', views.add_module_comment, name='add_module_comment'),
    path('<int:comment_id>/delete/', views.delete_comment, name='delete_comment'),
]