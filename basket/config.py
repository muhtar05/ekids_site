from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class BasketConfig(AppConfig):
    label = 'basket'
    name = 'basket'
    verbose_name = _('Корзина')
