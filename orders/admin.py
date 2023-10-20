from django.contrib import admin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    classes = ('grp-collapse grp-close',)
    raw_id_fields = ["module"]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["user", "paid", "created", "updated"]
    list_filter = ["paid", "created", "updated"]
    inlines = [OrderItemInline]

