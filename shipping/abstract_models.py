# -*- coding: utf-8 -*-
from decimal import Decimal as D

from django.db import models
from django.utils.translation import ugettext_lazy as _

from core_models.fields import AutoSlugField


class AbstractBase(models.Model):
    """
    Implements the interface declared by shipping.base.Base
    """
    code = AutoSlugField(_("Slug"), max_length=128, unique=True,
                         populate_from='name')
    name = models.CharField(_("Name"), max_length=128, unique=True)
    description = models.TextField(_("Description"), blank=True)

    # We allow shipping methods to be linked to a specific set of countries
    countries = models.ManyToManyField('address.Country',
                                       blank=True, verbose_name=_("Countries"))

    # We need this to mimic the interface of the Base shipping method
    is_discounted = False

    class Meta:
        abstract = True
        app_label = 'shipping'
        ordering = ['name']
        verbose_name = _("Shipping Method")
        verbose_name_plural = _("Shipping Methods")

    def __str__(self):
        return self.name

    def discount(self, basket):
        """
        Return the discount on the standard shipping charge
        """
        # This method is identical to the Base.discount().
        return D('0.00')






