from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class CatalogueConfig(AppConfig):
    label = 'catalogue'
    name = 'catalogue'
    verbose_name = _('Каталог')

    def ready(self):
        from . import receivers  # noqa
