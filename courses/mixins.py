from django.core.paginator import Paginator
from django.shortcuts import render
from django.views.generic.base import View
from watson import search as watson


class QuerySetSearchMixin(View):
    """Mixin по поиску среди моделей"""

    template_name = None
    partial_template_name = None
    objects_per_page = 10
    filter = None
    model = None

    def get_objects_per_page(self):
        """Количество объектов на странице"""
        return self.objects_per_page

    def get_queryset(self):
        qs = self.model.objects.none()
        return qs

    def get_filter_params(self, request):
        filter_params = {}
        return filter_params

    def get_filter(self, filter_params, qs):
        """Если требуется передать/внести данные перед инициализацией фильтра"""
        return None

    def get_q(self):
        """Если требуется передать/внести q параметр для поиска"""
        return self.request.GET.get("q")

    def get_context_data(self):
        """Дополнительные контекстные данные"""
        context = {}
        return context

    def get_context_data_with_qs(self, *args, **kwargs):
        """Доп. Контекстные данные если необходим отфильтрованный qs"""
        context = {}
        return context

    def get(self, request, *args, **kwargs):
        qs = self.get_queryset()  # Начальный queryset
        objects_per_page = self.get_objects_per_page()  # Кол-во объектов на странице

        ##############################################
        ########  Получение Get параметров ###########
        ##############################################

        page_num = request.GET.get("page", 1)
        q = self.get_q()  # Метод получения запроса поиска q
        if q and q != "None":
            qs = watson.filter(qs, q)

        filter_params = self.get_filter_params(request)

        if getattr(request, "htmx", False):
            f = self.get_filter(filter_params, qs) or (self.filter(filter_params, queryset=qs) if self.filter else None)
            filtered_queryset = f.qs if f else qs  # Отфильтрованный queryset через Watson и django-filter

            total_objects = filtered_queryset.count()

            try:
                page_int = int(page_num)
            except (ValueError, TypeError):
                page_int = 1

            left_to_load = total_objects - objects_per_page * page_int
            if left_to_load < 0:
                left_to_load = 0

            page = Paginator(filtered_queryset, objects_per_page).get_page(page_num)
            qs = page.object_list

            return render(
                request,
                self.partial_template_name,
                context={
                    "filter": f,
                    "page": page,
                    "page_obj": page,
                    "paginator": page.paginator,
                    "is_paginated": page.has_other_pages(),
                    "elided_page_range": page.paginator.get_elided_page_range(page.number, on_each_side=2, on_ends=1),
                    "start_count": (page.number - 1) * objects_per_page,  # для нумерации строк
                    "object_list": qs,
                    "courses": qs,
                    "q": q,
                    "total_objects": total_objects,
                    "left_to_load": left_to_load,
                    "objects_per_page": objects_per_page,
                    **self.get_context_data(),
                    **self.get_context_data_with_qs(filtered_queryset=filtered_queryset),
                    **filter_params,
                },
            )

        f = self.get_filter(filter_params, qs) or (self.filter(filter_params, queryset=qs) if self.filter else None)
        filtered_queryset = f.qs if f else qs  # Отфильтрованный queryset через Watson и django-filter

        page = Paginator(filtered_queryset, objects_per_page).get_page(page_num)
        total_objects = filtered_queryset.count()

        left_to_load = total_objects - objects_per_page
        if left_to_load < 0:
            left_to_load = 0
        qs = page.object_list

        return render(
            request,
            self.template_name,
            context={
                "filter": f,
                "page": page,
                "page_obj": page,
                "paginator": page.paginator,
                "is_paginated": page.has_other_pages(),
                "elided_page_range": page.paginator.get_elided_page_range(page.number, on_each_side=2, on_ends=1),
                "start_count": (page.number - 1) * objects_per_page,  # для нумерации строк
                "object_list": qs,
                "courses": qs,
                "q": q,
                "total_objects": total_objects,
                "left_to_load": left_to_load,
                "objects_per_page": objects_per_page,
                **self.get_context_data(),
                **self.get_context_data_with_qs(filtered_queryset=filtered_queryset),
                **filter_params,
            },
        )