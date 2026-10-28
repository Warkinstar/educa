from django import template

register = template.Library()


@register.filter
def app_label(obj):
    if not obj:
        return ""
    return obj._meta.app_label


@register.filter
def model_name(obj):
    if not obj:
        return ""
    return obj._meta.model_name