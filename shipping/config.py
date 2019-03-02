from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class ShippingConfig(AppConfig):
    label = 'shipping'
    name = 'shipping'
    verbose_name = _('Доставка')
