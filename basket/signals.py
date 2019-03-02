import django.dispatch
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from basket.models import Basket, BasketHistoryReserve, StockReserve

basket_addition = django.dispatch.Signal(
    providing_args=["product", "user", "request"])
voucher_addition = django.dispatch.Signal(
    providing_args=["basket", "voucher"])
voucher_removal = django.dispatch.Signal(
    providing_args=["basket", "voucher"])


@receiver(post_save, sender=StockReserve)
def check_status_basket(sender, instance, created, **kwargs):
    print("check status basket")
    print("Sender",sender, type(sender))
    print("Instance", instance, type(instance))
    print(kwargs)
