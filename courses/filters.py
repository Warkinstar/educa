import django_filters
from django import forms
from django.db.models import Q
from .models import Course, Subject


class CourseFilter(django_filters.FilterSet):
    # BaseCSVFilter / CharFilter не отбрасывает произвольные строки и slug
    subject = django_filters.BaseInFilter(
        method="filter_subjects",
        widget=forms.MultipleHiddenInput,
    )

    class Meta:
        model = Course
        fields = ["subject"]

    def filter_subjects(self, queryset, name, value):
        if not value:
            # Если BaseInFilter ничего не распарсил, проверяем сырые параметры GET
            request = getattr(self, "request", None)
            if request:
                raw_values = request.GET.getlist("subject")
            else:
                raw_values = []
            if not raw_values:
                return queryset
            value = raw_values

        ids = [v for v in value if str(v).isdigit()]
        slugs = [v for v in value if not str(v).isdigit()]

        query = Q()
        if ids:
            query |= Q(subject_id__in=ids)
        if slugs:
            query |= Q(subject__slug__in=slugs)

        return queryset.filter(query).distinct()
