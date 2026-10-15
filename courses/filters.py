import django_filters
from .models import Course, Subject

class CourseFilter(django_filters.FilterSet):
    subject = django_filters.ModelMultipleChoiceFilter(
        field_name="subject__slug",
        to_field_name="slug",
        queryset=Subject.objects.all(),
    )

    class Meta:
        model = Course
        fields = ["subject"]