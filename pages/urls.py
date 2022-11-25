from django.urls import path
from .views import HomePageView

urlpatterns = [path("main/", HomePageView.as_view(), name="home")]
