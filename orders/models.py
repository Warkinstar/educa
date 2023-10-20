from django.db import models
from django.conf import settings
from courses.models import Module


class Order(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="orders", on_delete=models.CASCADE
    )
    paid = models.BooleanField("Оплачено", default=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created"]
        indexes = [models.Index(fields=["-created"])]

    def __str__(self):
        return f"Order {self.id}"

    def get_total_cost(self):
        """Sum of all items(module_price)"""
        total = sum(item.price for item in self.items.all())
        return total


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order, related_name="items", on_delete=models.CASCADE, verbose_name="Заказ"
    )
    module = models.ForeignKey(
        Module,
        related_name="order_items",
        on_delete=models.CASCADE,
        verbose_name="Модуль",
    )
    price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Цена модуля"
    )

    def __str__(self):
        return str(self.id)
