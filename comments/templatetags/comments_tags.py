from django import template
from courses.templatetags.course import model_name

register = template.Library()

# Регистрируем импортированный фильтр, чтобы устранить дублирование
register.filter("model_name", model_name)


@register.filter
def app_label(obj):
    if not obj:
        return ""
    return obj._meta.app_label