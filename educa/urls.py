"""educa URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from courses.views import CourseListView
from django.views.generic.base import RedirectView
from django.http import HttpResponse
# from filebrowser.sites import site  # Отключено под Django 5


urlpatterns = [
    # path("admin/filebrowser/", site.urls),  # Отключено под Django 5  # /admin/filebrowser/browse/
    # path("grappelli/", include("grappelli.urls")),  # Отключено под Django 5
    path('favicon.ico', lambda request: HttpResponse(status=204)),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("course/", include("courses.urls")),
    path("", CourseListView.as_view(), name="course_list"),
    path("pages/", include("pages.urls")),
    path("__debug__/", include("debug_toolbar.urls")),
    path("api/", include("courses.api.urls", namespace="api")),
    path("tinymce", include("tinymce.urls")),
    path("chat/", include("chat.urls", namespace="chat")),
    path("quizes/", include("quizes.urls", namespace="quizes")),
    path('select2/', include('django_select2.urls')),
    path('comments/', include('comments.urls', namespace='comments')),
    
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
