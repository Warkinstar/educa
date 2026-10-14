from watson import search as watson

class QuerySetSearchMixin:
    filter = None
    partial_template_name = None
    objects_per_page = 9

    def get_template_names(self):
        if getattr(self.request, "htmx", False) and self.partial_template_name:
            return [self.partial_template_name]
        return [self.template_name]

    def get_paginate_by(self, queryset):
        return self.objects_per_page

    def get_queryset(self):
        queryset = super().get_queryset()

        if self.filter:
            self.filterset = self.filter(self.request.GET, queryset=queryset)
            queryset = self.filterset.qs

        query = self.request.GET.get("q", "").strip()
        if query:
            queryset = watson.filter(queryset, query)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if hasattr(self, "filterset"):
            context["filter"] = self.filterset
        return context