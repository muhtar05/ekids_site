import hashlib
from collections import OrderedDict
from decimal import Decimal as D

from catalogue.models import ContractorCatalogue
from django.conf import settings
from django.db import models
from django.db.models import Sum
from django.utils import timezone
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import pgettext_lazy

from core.compat import AUTH_USER_MODEL
from core.loading import get_model
from core.utils import get_default_currency
from core_models.fields import AutoSlugField

from address.models import Address

from . import exceptions


class RecallReason(models.Model):
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=50)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Причина перезвона'
        verbose_name_plural = 'Причины перезвона'


class CancelReason(models.Model):
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=50)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Причина отмены'
        verbose_name_plural = 'Причины отмена'


class Order(models.Model):
    """
    Модель для заказов
    """
    number = models.CharField(
        _("Order number"), max_length=128, db_index=True, unique=True)

    ORDER_TYPES = (
        ('callcenter', 'Заказ из колл центра'),
        ('basket', 'Заказ из корзины'),
        ('oneclick', 'Заказ в один клик')
    )

    type = models.CharField(max_length=30, choices=ORDER_TYPES, default='basket')

    site = models.ForeignKey(
        'sites.Site', verbose_name=_("Site"), null=True,
        on_delete=models.SET_NULL)

    basket = models.ForeignKey(
        'basket.Basket', verbose_name=_("Basket"),
        null=True, blank=True, on_delete=models.SET_NULL)

    # Orders can be placed without the user authenticating so we don't always
    # have a customer ID.
    user = models.ForeignKey(
        AUTH_USER_MODEL, related_name='orders', null=True, blank=True,
        verbose_name=_("User"), on_delete=models.SET_NULL)

    # Billing address is not always required (eg paying by gift card)
    billing_address = models.ForeignKey(
        'order.BillingAddress', null=True, blank=True,
        verbose_name=_("Billing Address"),
        on_delete=models.SET_NULL)

    # Total price looks like it could be calculated by adding up the
    # prices of the associated lines, but in some circumstances extra
    # order-level charges are added and so we need to store it separately
    currency = models.CharField(
        _("Currency"), max_length=12, default=get_default_currency)
    # Итоговая сумма заказа c вычетом скидки (меньше)
    total_incl_tax = models.DecimalField(
        _("Order total (inc. tax)"), decimal_places=2, max_digits=12)
    # Итоговая сумма заказа без вычета скидки (больше)
    total_excl_tax = models.DecimalField(
        _("Order total (excl. tax)"), decimal_places=2, max_digits=12)

    promo_discount = models.DecimalField("Сумма скидки по промокоду", decimal_places=2, max_digits=12, null=True)

    # Цена доставки
    shipping_incl_tax = models.DecimalField(
        _("Shipping charge (inc. tax)"), decimal_places=2, max_digits=12,
        default=0)
    shipping_excl_tax = models.DecimalField(
        _("Shipping charge (excl. tax)"), decimal_places=2, max_digits=12,
        default=0)
    post_id = models.ForeignKey('logistics_exchange.Office', blank=True, null=True, on_delete=models.SET_NULL)
    post_id_pick = models.ForeignKey('logistics_exchange.OfficePickPoint', blank=True, null=True, on_delete=models.SET_NULL)
    # Not all lines are actually shipped (such as downloads), hence shipping
    # address is not mandatory.
    shipping_address = models.ForeignKey(
        'order.ShippingAddress', null=True, blank=True,
        verbose_name=_("Shipping Address"),
        on_delete=models.SET_NULL)

    # Тип доставки
    shipping_method = models.ForeignKey('ShipmentMethod',
                                        null=True, blank=True,
                                        on_delete=models.SET_NULL)

    # Identifies shipping code
    shipping_code = models.CharField(blank=True, max_length=128, default="")

    # Use this field to indicate that an order is on hold / awaiting payment
    # status = models.CharField(_("Status"), max_length=100, blank=True)
    status = models.ForeignKey(
        'OrderStatus', verbose_name=_("Status"), null=True,
        on_delete=models.SET_NULL)
    date_delivery_status = models.DateTimeField(null=True, blank=True, db_index=True)

    payment_status = models.ForeignKey(
        'PaymentStatus', verbose_name=_("Payment Status"), null=True,
        on_delete=models.SET_NULL)
    # Способ оплаты 1-Наличные 2-Безналичные
    payment_type = models.ForeignKey(
        'PaymentType', verbose_name=_("Payment Type"), null=True,
        on_delete=models.SET_NULL)

    shipment_status = models.ForeignKey(
        'ShipmentStatus', verbose_name=_("Shipment Status"), null=True,
        on_delete=models.SET_NULL, blank=True)
    guest_email = models.EmailField(_("Guest email address"), blank=True)

    date_placed = models.DateTimeField(db_index=True)
    pipeline = getattr(settings, 'OSCAR_ORDER_STATUS_PIPELINE', {})
    cascade = getattr(settings, 'OSCAR_ORDER_STATUS_CASCADE', {})

    comment = models.CharField(max_length=128, default='Default', null=True, blank=True)
    call_st = models.BooleanField(_("Call Centr status"), default=False)

    DONE, UNDONE, REWORK = 'done', 'undone', 'rework'
    INFO_STATUSES = (
        (DONE, 'Обработан'),
        (UNDONE, 'Не обработан'),
        (REWORK, 'Отложен'),
    )

    info_status = models.CharField(max_length=50, choices=INFO_STATUSES, default=UNDONE)
    comment_info = models.TextField(blank=True, null=True)
    order_comment = models.TextField(blank=True, null=True)

    CONFIRM, RECALL, CANCEL = 'confirm', 'recall', 'cancel'
    CALL_CENTR_STATUSES = (
        (CONFIRM, 'Подтвержден'),
        (RECALL, 'Перезвонить'),
        (CANCEL, 'Отменен'),
    )

    call_centr_status = models.CharField(max_length=30, choices=CALL_CENTR_STATUSES,
                                         null=True, blank=True)
    recall_time = models.DateTimeField(null=True, blank=True)
    recall_comment = models.TextField(blank=True, null=True)
    recall_reason = models.ForeignKey(RecallReason, null=True, blank=True)
    cancel_reason = models.ForeignKey(CancelReason, null=True, blank=True)
    cancel_comment = models.TextField(blank=True, null=True)
    comment_operator_call_centr = models.TextField(blank=True, null=True)
    delivery_date = models.DateField(blank=True, null=True)
    customer_name = models.CharField('Имя покупателя(если заказ в один клик)', max_length=255, null=True,blank=True)

    INTERVALS_VARIANTS = (
        ('9-18', '9.00-18.00'),
        ('9-14', '9.00-14.00'),
        ('13-18', '13.00-18.00'),
        ('9-22', '9.00-22.00'),
        ('18-22', '18.00-22.00 (доп. оплата)')
    )
    delivery_time_interval = models.CharField(max_length=30, choices=INTERVALS_VARIANTS, blank=True, null=True)
    phone = models.CharField(max_length=50, null=True, blank=True)
    extra_phone = models.CharField(max_length=50, null=True, blank=True)
    busy_status = models.BooleanField(default=False)
    phone_callcentr = models.CharField(max_length=50, null=True, blank=True)
    is_delivery = models.BooleanField(default=False)
    procure_datetime = models.DateTimeField(null=True, blank=True)
    order_from_callcenter = models.BooleanField('Заказ сделан через колл центр', default=False)

    NONE, READY, PROBLEM, MOVED, IN_PROCESS, DELIVERED_DPD, CANCELED, DELIVERED_OWN = 0, 1, 2, 3, 4, 5, 6, 7
    ORDER_DRIVER_STATUS_CHOICES = (
        (NONE, 'Нет'),
        (READY, 'Готов к отправке'),
        (PROBLEM, 'Проблемный'),
        (MOVED, 'Перенесен'),
        (IN_PROCESS, 'В процессе сборки'),
        (DELIVERED_DPD, 'Сдан в логистическую компанию'),
        (CANCELED, 'Снят с доставки'),
        (DELIVERED_OWN, 'Заказ доставлен, оплачен'),
    )
    default_order_driver_status = NONE
    order_driver_status = models.SmallIntegerField('Статус водителя', choices=ORDER_DRIVER_STATUS_CHOICES,
                                             default=default_order_driver_status)
    order_cancel_reason = models.TextField(_('Причина отмены заказа'), blank=True)
    order_move_reason = models.TextField(_('Причина переноса заказа'), blank=True)
    dpd_nomen = models.CharField(max_length=255, null=True, blank=True)
    is_dpd_received = models.BooleanField(default=False, blank=True)

    NONE, DRIVER, CASHBOX = 0, 1, 2
    MONEY_STATUS_CHOICES = (
        (NONE, 'Нет'),
        (DRIVER, 'У водителя'),
        (CASHBOX, 'В кассе'),
    )
    default_money_status = NONE
    money_status = models.SmallIntegerField('Статус денег', choices=MONEY_STATUS_CHOICES,
                                            default=default_money_status)

    NONE, DPD, OWN = 0, 1, 2
    DELIVERY_TYPE_CHOICES = (
        (NONE, 'Нет'),
        (DPD, 'В DPD'),
        (OWN, 'Своими силами'),
    )
    default_delivery_type = NONE
    delivery_type = models.SmallIntegerField('Тип доставки', choices=DELIVERY_TYPE_CHOICES,
                                             default=default_delivery_type)

    class Meta:
        app_label = 'order'
        ordering = ['-date_placed']
        verbose_name = _("Заказ")
        verbose_name_plural = _("Заказы")

    def __str__(self):
        return "#%s" % (self.number,)

    def intervals_choices(self):
        return dict(Order.INTERVALS_VARIANTS)[self.dalivery_time_interval]

    def get_total_sum_with_discounts(self):
        total = D('0.00')
        for line in self.lines.all():
            total += line.line_price_excl_tax
        if self.promo_discount:
            total -= self.promo_discount
        return total

    def get_discount_for_order(self):
        total = D('0.00')
        for line in self.lines.all():
            total += line.line_price_before_discounts_excl_tax - line.line_price_excl_tax
        return total

    @classmethod
    def all_statuses(cls):
        """
        Return all possible statuses for an order
        """
        return list(cls.pipeline.keys())

    def get_total_opt_sum(self):
        total = D('0.00')
        for line in self.lines.all():
            current_product = line.product
            if current_product.price_opt:
                total += current_product.price_opt * line.quantity
            else:
                good = line.product.get_related_good()
                if good.price_opt:
                    total += good.price_opt * line.quantity
        return total

    def available_statuses(self):
        """
        Return all possible statuses that this order can move to
        """
        return OrderStatus.objects.values_list('name', flat=True)
        # return self.pipeline.get(self.status, ())

    def available_payment_statuses(self):
        """
        Return all possible statuses that this order can move to
        """
        return PaymentStatus.objects.values_list('name', flat=True)

    def set_status(self, new_status):
        """
        Set a new status for this order.

        If the requested status is not valid, then ``InvalidOrderStatus`` is
        raised.
        """
        if new_status == self.status.name:
            return
        if new_status not in self.available_statuses():
            raise exceptions.InvalidOrderStatus(
                _("'%(new_status)s' is not a valid status for order %(number)s"
                  " (current status: '%(status)s')")
                % {'new_status': new_status,
                   'number': self.number,
                   'status': self.status})
        new_status_get = OrderStatus.objects.filter(name=new_status).first()
        self.status = new_status_get
        self.save()

    def set_payment_status(self, new_status):
        """
        Set a new status for this order.

        If the requested status is not valid, then ``InvalidOrderStatus`` is
        raised.
        """
        if new_status == self.status.name:
            return
        if new_status not in self.available_payment_statuses():
            raise exceptions.InvalidOrderStatus(
                _("'%(new_status)s' is not a valid status for order %(number)s"
                  " (current status: '%(status)s')")
                % {'new_status': new_status,
                   'number': self.number,
                   'status': self.status})
        new_status_get = PaymentStatus.objects.filter(name=new_status).first()
        self.status = new_status_get
        self.save()

    set_status.alters_data = True

    @property
    def is_anonymous(self):
        # It's possible for an order to be placed by a customer who then
        # deletes their profile.  Hence, we need to check that a guest email is
        # set.
        return self.user is None and bool(self.guest_email)

    @property
    def basket_total_before_discounts_incl_tax(self):
        """
        Return basket total including tax but before discounts are applied
        """
        total = D('0.00')
        for line in self.lines.all():
            total += line.line_price_before_discounts_incl_tax
        return total

    @property
    def basket_total_before_discounts_excl_tax(self):
        """
        Return basket total excluding tax but before discounts are applied
        """
        total = D('0.00')
        for line in self.lines.all():
            total += line.line_price_before_discounts_excl_tax
        return total

    @property
    def basket_total_incl_tax(self):
        """
        Return basket total including tax
        """
        return self.total_incl_tax - self.shipping_incl_tax

    @property
    def basket_total_excl_tax(self):
        """
        Return basket total excluding tax
        """
        return self.total_excl_tax - self.shipping_excl_tax

    @property
    def total_before_discounts_incl_tax(self):
        return (self.basket_total_before_discounts_incl_tax +
                self.shipping_incl_tax)

    @property
    def total_before_discounts_excl_tax(self):
        return (self.basket_total_before_discounts_excl_tax +
                self.shipping_excl_tax)

    @property
    def total_discount_incl_tax(self):
        """
        The amount of discount this order received
        """
        discount = D('0.00')
        for line in self.lines.all():
            discount += line.line_price_incl_tax
        # print("total discount = ", discount)
        return discount

    @property
    def total_discount_excl_tax(self):
        discount = D('0.00')
        for line in self.lines.all():
            discount += line.discount_excl_tax
        return discount

    @property
    def total_tax(self):
        return self.total_incl_tax - self.total_excl_tax

    @property
    def num_lines(self):
        return self.lines.count()

    @property
    def num_items(self):
        """
        Returns the number of items in this order.
        """
        num_items = 0
        for line in self.lines.all():
            num_items += line.quantity
        return num_items

    @property
    def shipping_tax(self):
        return self.shipping_incl_tax - self.shipping_excl_tax

    @property
    def shipping_status(self):
        """Return the last complete shipping event for this order."""

        # As safeguard against identical timestamps, also sort by the primary
        # key. It's not recommended to rely on this behaviour, but in practice
        # reasonably safe if PKs are not manually set.
        events = self.shipping_events.order_by('-date_created', '-pk').all()
        if not len(events):
            return ''

        # Collect all events by event-type
        event_map = OrderedDict()
        for event in events:
            event_name = event.event_type.name
            if event_name not in event_map:
                event_map[event_name] = []
            event_map[event_name].extend(list(event.line_quantities.all()))

        # Determine last complete event
        status = _("In progress")
        for event_name, event_line_quantities in event_map.items():
            if self._is_event_complete(event_line_quantities):
                return event_name
        return status

    @property
    def has_shipping_discounts(self):
        return len(self.shipping_discounts) > 0

    @property
    def shipping_before_discounts_incl_tax(self):
        # We can construct what shipping would have been before discounts by
        # adding the discounts back onto the final shipping charge.
        total = D('0.00')
        for discount in self.shipping_discounts:
            total += discount.amount
        return self.shipping_incl_tax + total

    def _is_event_complete(self, event_quantities):
        # Form map of line to quantity
        event_map = {}
        for event_quantity in event_quantities:
            line_id = event_quantity.line_id
            event_map.setdefault(line_id, 0)
            event_map[line_id] += event_quantity.quantity

        for line in self.lines.all():
            if event_map.get(line.pk, 0) != line.quantity:
                return False
        return True

    def verification_hash(self):
        key = '%s%s' % (self.number, settings.SECRET_KEY)
        hash = hashlib.md5(key.encode('utf8'))
        return hash.hexdigest()

    @property
    def email(self):
        if not self.user:
            return self.guest_email
        return self.user.email

    @property
    def basket_discounts(self):
        return self.discounts.filter(category=OrderDiscount.BASKET)

    @property
    def shipping_discounts(self):
        return self.discounts.filter(category=OrderDiscount.SHIPPING)

    @property
    def post_order_actions(self):
        return self.discounts.filter(category=OrderDiscount.DEFERRED)

    def set_date_placed_default(self):
        if self.date_placed is None:
            self.date_placed = now()

    def save(self, *args, **kwargs):
        self.set_date_placed_default()
        super(Order, self).save(*args, **kwargs)


class OrderNote(models.Model):
    """
    A note against an order.

    This are often used for audit purposes too.  IE, whenever an admin
    makes a change to an order, we create a note to record what happened.
    """
    order = models.ForeignKey('order.Order', related_name="notes",
                              verbose_name=_("Order"))

    user = models.ForeignKey(AUTH_USER_MODEL, null=True,
                             verbose_name=_("User"))

    # We allow notes to be classified although this isn't always needed
    INFO, WARNING, ERROR, SYSTEM = 'Info', 'Warning', 'Error', 'System'
    note_type = models.CharField(_("Note Type"), max_length=128, blank=True)

    message = models.TextField(_("Message"))
    date_created = models.DateTimeField(_("Date Created"), auto_now_add=True)
    date_updated = models.DateTimeField(_("Date Updated"), auto_now=True)

    # Notes can only be edited for 5 minutes after being created
    editable_lifetime = 300

    class Meta:
        app_label = 'order'
        verbose_name = _("Заметка о заказе")
        verbose_name_plural = _("Заметки о заказах")

    def __str__(self):
        return "'%s' (%s)" % (self.message[0:50], self.user)

    def is_editable(self):
        if self.note_type == self.SYSTEM:
            return False
        delta = timezone.now() - self.date_updated
        return delta.seconds < self.editable_lifetime


class CommunicationEvent(models.Model):
    """
    An order-level event involving a communication to the customer, such
    as an confirmation email being sent.
    """
    order = models.ForeignKey(
        'order.Order', related_name="communication_events",
        verbose_name=_("Order"))
    event_type = models.ForeignKey(
        'customer.CommunicationEventType', verbose_name=_("Event Type"))
    date_created = models.DateTimeField(_("Date"), auto_now_add=True)

    class Meta:
        app_label = 'order'
        verbose_name = _("Communication Event")
        verbose_name_plural = _("Communication Events")
        ordering = ['-date_created']

    def __str__(self):
        return _("'%(type)s' event for order #%(number)s") \
               % {'type': self.event_type.name, 'number': self.order.number}


class ChangeLine(models.Model):
    order = models.ForeignKey(
        'order.Order', related_name='change_lines', verbose_name=_("Заказ"))

    partner = models.ForeignKey(
        'partner.Partner', related_name='change_order_lines', blank=True, null=True,
        on_delete=models.SET_NULL, verbose_name=_("Partner"))

    partner_name = models.CharField(
        _("Partner name"), max_length=128, blank=True)

    partner_sku = models.CharField(_("Partner SKU"), max_length=128)

    partner_line_reference = models.CharField(
        _("Partner reference"), max_length=128, blank=True)
    partner_line_notes = models.TextField(
        _("Partner Notes"), blank=True)

    stockrecord = models.ForeignKey(
        'partner.StockRecord', on_delete=models.SET_NULL, blank=True,
        null=True, verbose_name=_("Stock record"))

    product = models.ForeignKey(
        'catalogue.Product', on_delete=models.SET_NULL, blank=True, null=True,
        verbose_name=_("Product"))

    title = models.CharField(
        pgettext_lazy("Product title", "Title"), max_length=255)
    # UPC can be null because it's usually set as the product's UPC, and that
    # can be null as well
    upc = models.CharField(_("UPC"), max_length=128, blank=True, null=True)

    quantity = models.PositiveIntegerField(_("Quantity"), default=1)
    quantity_undelivered = models.PositiveIntegerField(_('Quantity_Undelivered'), default=0, null=True)

    # REPORTING INFORMATION
    # ---------------------

    # Price information (these fields are actually redundant as the information
    # can be calculated from the LinePrice models
    line_price_incl_tax = models.DecimalField(
        _("Price (inc. tax)"), decimal_places=2, max_digits=12)
    line_price_excl_tax = models.DecimalField(
        _("Price (excl. tax)"), decimal_places=2, max_digits=12)

    # Price information before discounts are applied
    line_price_before_discounts_incl_tax = models.DecimalField(
        _("Price before discounts (inc. tax)"),
        decimal_places=2, max_digits=12)
    line_price_before_discounts_excl_tax = models.DecimalField(
        _("Price before discounts (excl. tax)"),
        decimal_places=2, max_digits=12)

    # Cost price (the price charged by the fulfilment partner for this
    # product).
    unit_cost_price = models.DecimalField(
        _("Unit Cost Price"), decimal_places=2, max_digits=12, blank=True,
        null=True)
    # Normal site price for item (without discounts)
    unit_price_incl_tax = models.DecimalField(
        _("Unit Price (inc. tax)"), decimal_places=2, max_digits=12,
        blank=True, null=True)
    unit_price_excl_tax = models.DecimalField(
        _("Unit Price (excl. tax)"), decimal_places=2, max_digits=12,
        blank=True, null=True)
    # Retail price at time of purchase
    unit_retail_price = models.DecimalField(
        _("Unit Retail Price"), decimal_places=2, max_digits=12,
        blank=True, null=True)

    NEW, REMOVE, DEFAULT = 'new', 'remove', 'default'
    INFO_STATUSES = (
        (DEFAULT, 'По умолчанию'),
        (NEW, 'Новый'),
        (REMOVE, 'Удален'),
    )

    YES, NO, CUSTOM = 'yes', 'no', 'custom'
    AVAILABILITY_STATUSES = (
        (YES, 'Да'),
        (NO, 'Нет'),
        (CUSTOM, 'Под заказ'),
    )

    info_status = models.CharField(max_length=50, choices=INFO_STATUSES, default=DEFAULT)
    comment_info = models.TextField(blank=True, null=True)
    stock_availability = models.CharField(max_length=10, choices=AVAILABILITY_STATUSES, null=True, blank=True)

    class Meta:
        app_label = 'order'
        ordering = ['pk']
        verbose_name = _("Измененная Строка заказа")
        verbose_name_plural = _("Измененные Строки заказа")

# LINES


class Line(models.Model):
    """
    An order line
    """
    order = models.ForeignKey(
        'order.Order', related_name='lines', verbose_name=_("Order"))

    # PARTNER INFORMATION
    # -------------------
    # We store the partner and various detail their SKU and the title for cases
    # where the product has been deleted from the catalogue (but we still need
    # the data for reporting).  We also store the partner name in case the
    # partner gets deleted at a later date.

    partner = models.ForeignKey(
        'partner.Partner', related_name='order_lines', blank=True, null=True,
        on_delete=models.SET_NULL, verbose_name=_("Partner"))
    partner_name = models.CharField(
        _("Partner name"), max_length=128, blank=True)
    partner_sku = models.CharField(_("Partner SKU"), max_length=128)

    # A line reference is the ID that a partner uses to represent this
    # particular line (it's not the same as a SKU).
    partner_line_reference = models.CharField(
        _("Partner reference"), max_length=128, blank=True,
        help_text=_("This is the item number that the partner uses "
                    "within their system"))
    partner_line_notes = models.TextField(
        _("Partner Notes"), blank=True)

    # We keep a link to the stockrecord used for this line which allows us to
    # update stocklevels when it ships
    stockrecord = models.ForeignKey(
        'partner.StockRecord', on_delete=models.SET_NULL, blank=True,
        null=True, verbose_name=_("Stock record"))

    # PRODUCT INFORMATION
    # -------------------

    # We don't want any hard links between orders and the products table so we
    # allow this link to be NULLable.
    product = models.ForeignKey(
        'catalogue.Product', on_delete=models.SET_NULL, blank=True, null=True,
        verbose_name=_("Product"))
    title = models.CharField(
        pgettext_lazy("Product title", "Title"), max_length=255)
    # UPC can be null because it's usually set as the product's UPC, and that
    # can be null as well
    upc = models.CharField(_("UPC"), max_length=128, blank=True, null=True)

    quantity = models.PositiveIntegerField(_("Quantity"), default=1)
    quantity_from_chado_storage = models.PositiveIntegerField(_('Количество товаров со склада'), default=0)
    quantity_undelivered = models.PositiveIntegerField(_('Quantity_Undelivered'), default=0, null=True)

    NONE, TAKEN, CANCELED, MOVED, REMOVED = 0, 1, 2, 3, 4
    DRIVER_STATUS_CHOICES = (
        (NONE, 'Нет'),
        (TAKEN, 'Забрал'),
        (CANCELED, 'Отменен'),
        (MOVED, 'Перенесен'),
        (REMOVED, 'Удален'),
    )
    default_driver_status = NONE
    driver_status = models.SmallIntegerField('Статус водителя', choices=DRIVER_STATUS_CHOICES,
                                             default=default_driver_status)
    cancel_reason = models.TextField(_('Причина отмены'), blank=True)
    move_reason = models.TextField(_('Причина переноса'), blank=True)

    # Стоимость заказа с учетом скидки
    line_price_incl_tax = models.DecimalField(
        _("Price (inc. tax)"), decimal_places=2, max_digits=12)
    line_price_excl_tax = models.DecimalField(
        _("Price (excl. tax)"), decimal_places=2, max_digits=12)

    # Стоимость линии заказа без скидки
    line_price_before_discounts_incl_tax = models.DecimalField(
        _("Price before discounts (inc. tax)"),
        decimal_places=2, max_digits=12)
    line_price_before_discounts_excl_tax = models.DecimalField(
        _("Price before discounts (excl. tax)"),
        decimal_places=2, max_digits=12)

    # Cost price (the price charged by the fulfilment partner for this
    # product).
    unit_cost_price = models.DecimalField(
        _("Unit Cost Price"), decimal_places=2, max_digits=12, blank=True,
        null=True)

    unit_opt_price = models.DecimalField('Закупочная цена товара', decimal_places=2, max_digits=12, blank=True, null=True)
    # цена товара со скидкой
    unit_price_with_discount = models.DecimalField('Цена товара со скидкой', decimal_places=2, max_digits=12, blank=True, null=True)

    # Normal site price for item (without discounts)
    unit_price_incl_tax = models.DecimalField(
        _("Unit Price (inc. tax)"), decimal_places=2, max_digits=12,
        blank=True, null=True)

    unit_price_excl_tax = models.DecimalField(
        _("Unit Price (excl. tax)"), decimal_places=2, max_digits=12,
        blank=True, null=True)
    # Retail price at time of purchase
    unit_retail_price = models.DecimalField(
        _("Unit Retail Price"), decimal_places=2, max_digits=12,
        blank=True, null=True)

    # Partners often want to assign some status to each line to help with their
    # own business processes.
    status = models.CharField(_("Status"), max_length=255, blank=True)

    # Estimated dispatch date - should be set at order time
    est_dispatch_date = models.DateField(
        _("Estimated Dispatch Date"), blank=True, null=True)

    NEW, REMOVE, DEFAULT = 'new', 'remove', 'default'
    INFO_STATUSES = (
        (DEFAULT, 'По умолчанию'),
        (NEW, 'Новый'),
        (REMOVE, 'Удален'),
    )

    YES, NO, CUSTOM = 'yes', 'no', 'custom'
    AVAILABILITY_STATUSES = (
        (YES, 'Да'),
        (NO, 'Нет'),
        (CUSTOM, 'Под заказ'),
    )

    info_status = models.CharField(max_length=50, choices=INFO_STATUSES, default=DEFAULT)
    comment_info = models.TextField(blank=True, null=True)
    stock_availability = models.CharField(max_length=10, choices=AVAILABILITY_STATUSES, null=True, blank=True)
    #: Order status pipeline.  This should be a dict where each (key, value)
    #: corresponds to a status and the possible statuses that can follow that
    #: one.
    pipeline = getattr(settings, 'OSCAR_LINE_STATUS_PIPELINE', {})

    class Meta:
        app_label = 'order'
        ordering = ['pk']
        verbose_name = _("Строка заказа")
        verbose_name_plural = _("Строки заказа")

    def __str__(self):
        if self.product:
            title = self.product.title
        else:
            title = _('<missing product>')
        return _("Product '%(name)s', quantity '%(qty)s'") % {
            'name': title, 'qty': self.quantity}

    @classmethod
    def all_statuses(cls):
        """
        Return all possible statuses for an order line
        """
        return list(cls.pipeline.keys())

    def available_statuses(self):
        """
        Return all possible statuses that this order line can move to
        """
        return self.pipeline.get(self.status, ())

    def set_status(self, new_status):
        """
        Set a new status for this line

        If the requested status is not valid, then ``InvalidLineStatus`` is
        raised.
        """
        if new_status == self.status:
            return
        if new_status not in self.available_statuses():
            raise exceptions.InvalidLineStatus(
                _("'%(new_status)s' is not a valid status (current status:"
                  " '%(status)s')")
                % {'new_status': new_status, 'status': self.status})
        self.status = new_status
        self.save()

    set_status.alters_data = True

    @property
    def category(self):
        """
        Used by Google analytics tracking
        """
        return None

    @property
    def description(self):
        """
        Returns a description of this line including details of any
        line attributes.
        """
        desc = self.title
        ops = []
        for attribute in self.attributes.all():
            ops.append("%s = '%s'" % (attribute.type, attribute.value))
        if ops:
            desc = "%s (%s)" % (desc, ", ".join(ops))
        return desc

    def sum_price(self):
        return self.line_price_incl_tax * self.quantity

    @property
    def discount_incl_tax(self):
        return self.line_price_before_discounts_incl_tax \
               - self.line_price_incl_tax

    @property
    def discount_excl_tax(self):
        return self.line_price_before_discounts_excl_tax \
               - self.line_price_excl_tax

    @property
    def line_price_tax(self):
        return self.line_price_incl_tax - self.line_price_excl_tax

    @property
    def unit_price_tax(self):
        return self.unit_price_incl_tax - self.unit_price_excl_tax

    # Shipping status helpers

    @property
    def shipping_status(self):
        """
        Returns a string summary of the shipping status of this line
        """
        status_map = self.shipping_event_breakdown
        if not status_map:
            return ''

        events = []
        last_complete_event_name = None
        for event_dict in reversed(list(status_map.values())):
            if event_dict['quantity'] == self.quantity:
                events.append(event_dict['name'])
                last_complete_event_name = event_dict['name']
            else:
                events.append("%s (%d/%d items)" % (
                    event_dict['name'], event_dict['quantity'],
                    self.quantity))

        if last_complete_event_name == list(status_map.values())[0]['name']:
            return last_complete_event_name

        return ', '.join(events)

    def is_shipping_event_permitted(self, event_type, quantity):
        """
        Test whether a shipping event with the given quantity is permitted

        This method should normally be overriden to ensure that the
        prerequisite shipping events have been passed for this line.
        """
        # Note, this calculation is simplistic - normally, you will also need
        # to check if previous shipping events have occurred.  Eg, you can't
        # return lines until they have been shipped.
        current_qty = self.shipping_event_quantity(event_type)
        return (current_qty + quantity) <= self.quantity

    def shipping_event_quantity(self, event_type):
        """
        Return the quantity of this line that has been involved in a shipping
        event of the passed type.
        """
        result = self.shipping_event_quantities.filter(
            event__event_type=event_type).aggregate(Sum('quantity'))
        if result['quantity__sum'] is None:
            return 0
        else:
            return result['quantity__sum']

    def has_shipping_event_occurred(self, event_type, quantity=None):
        """
        Test whether this line has passed a given shipping event
        """
        if not quantity:
            quantity = self.quantity
        return self.shipping_event_quantity(event_type) == quantity

    def get_event_quantity(self, event):
        """
        Fetches the ShippingEventQuantity instance for this line

        Exists as a separate method so it can be overridden to avoid
        the DB query that's caused by get().
        """
        return event.line_quantities.get(line=self)

    @property
    def shipping_event_breakdown(self):
        """
        Returns a dict of shipping events that this line has been through
        """
        status_map = OrderedDict()
        for event in self.shipping_events.all():
            event_type = event.event_type
            event_name = event_type.name
            event_quantity = self.get_event_quantity(event).quantity
            if event_name in status_map:
                status_map[event_name]['quantity'] += event_quantity
            else:
                status_map[event_name] = {
                    'event_type': event_type,
                    'name': event_name,
                    'quantity': event_quantity
                }
        return status_map

    # Payment event helpers

    def is_payment_event_permitted(self, event_type, quantity):
        """
        Test whether a payment event with the given quantity is permitted.

        Allow each payment event type to occur only once per quantity.
        """
        current_qty = self.payment_event_quantity(event_type)
        return (current_qty + quantity) <= self.quantity

    def payment_event_quantity(self, event_type):
        """
        Return the quantity of this line that has been involved in a payment
        event of the passed type.
        """
        result = self.payment_event_quantities.filter(
            event__event_type=event_type).aggregate(Sum('quantity'))
        if result['quantity__sum'] is None:
            return 0
        else:
            return result['quantity__sum']

    @property
    def is_product_deleted(self):
        return self.product is None

    def is_available_to_reorder(self, basket, strategy):
        """
        Test if this line can be re-ordered using the passed strategy and
        basket
        """
        if not self.product:
            return False, (_("'%(title)s' is no longer available") %
                           {'title': self.title})

        try:
            basket_line = basket.lines.get(product=self.product)
        except basket.lines.model.DoesNotExist:
            desired_qty = self.quantity
        else:
            desired_qty = basket_line.quantity + self.quantity

        result = strategy.fetch_for_product(self.product)
        is_available, reason = result.availability.is_purchase_permitted(
            quantity=desired_qty)
        if not is_available:
            return False, reason
        return True, None


class LineAttribute(models.Model):
    """
    An attribute of a line
    """
    line = models.ForeignKey(
        'order.Line', related_name='attributes',
        verbose_name=_("Line"))
    option = models.ForeignKey(
        'catalogue.Option', null=True, on_delete=models.SET_NULL,
        related_name="line_attributes", verbose_name=_("Option"))
    type = models.CharField(_("Type"), max_length=128)
    value = models.CharField(_("Value"), max_length=255)

    class Meta:
        app_label = 'order'
        verbose_name = _("Атрибут строки заказа")
        verbose_name_plural = _("Атрибуты строк заказа")

    def __str__(self):
        return "%s = %s" % (self.type, self.value)


class LinePrice(models.Model):
    """
    For tracking the prices paid for each unit within a line.

    This is necessary as offers can lead to units within a line
    having different prices.  For example, one product may be sold at
    50% off as it's part of an offer while the remainder are full price.
    """
    order = models.ForeignKey(
        'order.Order', related_name='line_prices', verbose_name=_("Option"))
    line = models.ForeignKey(
        'order.Line', related_name='prices', verbose_name=_("Line"))
    quantity = models.PositiveIntegerField(_("Quantity"), default=1)
    price_incl_tax = models.DecimalField(
        _("Price (inc. tax)"), decimal_places=2, max_digits=12)
    price_excl_tax = models.DecimalField(
        _("Price (excl. tax)"), decimal_places=2, max_digits=12)
    shipping_incl_tax = models.DecimalField(
        _("Shiping (inc. tax)"), decimal_places=2, max_digits=12, default=0)
    shipping_excl_tax = models.DecimalField(
        _("Shipping (excl. tax)"), decimal_places=2, max_digits=12, default=0)

    class Meta:
        # abstract = True
        app_label = 'order'
        ordering = ('id',)
        verbose_name = _("Line Price")
        verbose_name_plural = _("Line Prices")

    def __str__(self):
        return _("Line '%(number)s' (quantity %(qty)d) price %(price)s") % {
            'number': self.line,
            'qty': self.quantity,
            'price': self.price_incl_tax}


# PAYMENT EVENTS


class PaymentEventType(models.Model):
    """
    Payment event types are things like 'Paid', 'Failed', 'Refunded'.

    These are effectively the transaction types.
    """
    name = models.CharField(_("Name"), max_length=128, unique=True)
    code = AutoSlugField(_("Code"), max_length=128, unique=True,
                         populate_from='name')

    class Meta:
        app_label = 'order'
        verbose_name = _("Payment Event Type")
        verbose_name_plural = _("Payment Event Types")
        ordering = ('name',)

    def __str__(self):
        return self.name


class PaymentEvent(models.Model):
    """
    A payment event for an order

    For example:

    * All lines have been paid for
    * 2 lines have been refunded
    """
    order = models.ForeignKey(
        'order.Order', related_name='payment_events',
        verbose_name=_("Order"))
    amount = models.DecimalField(
        _("Amount"), decimal_places=2, max_digits=12)
    # The reference should refer to the transaction ID of the payment gateway
    # that was used for this event.
    reference = models.CharField(
        _("Reference"), max_length=128, blank=True)
    lines = models.ManyToManyField(
        'order.Line', through='PaymentEventQuantity',
        verbose_name=_("Lines"))
    event_type = models.ForeignKey(
        'order.PaymentEventType', verbose_name=_("Event Type"))
    # Allow payment events to be linked to shipping events.  Often a shipping
    # event will trigger a payment event and so we can use this FK to capture
    # the relationship.
    shipping_event = models.ForeignKey(
        'order.ShippingEvent', related_name='payment_events',
        null=True)
    date_created = models.DateTimeField(_("Date created"), auto_now_add=True)

    class Meta:
        app_label = 'order'
        verbose_name = _("Payment Event")
        verbose_name_plural = _("Payment Events")
        ordering = ['-date_created']

    def __str__(self):
        return _("Payment event for order %s") % self.order

    def num_affected_lines(self):
        return self.lines.all().count()


class PaymentEventQuantity(models.Model):
    """
    A "through" model linking lines to payment events
    """
    event = models.ForeignKey(
        'order.PaymentEvent', related_name='line_quantities',
        verbose_name=_("Event"))
    line = models.ForeignKey(
        'order.Line', related_name="payment_event_quantities",
        verbose_name=_("Line"))
    quantity = models.PositiveIntegerField(_("Quantity"))

    class Meta:
        app_label = 'order'
        verbose_name = _("Payment Event Quantity")
        verbose_name_plural = _("Payment Event Quantities")
        unique_together = ('event', 'line')


# SHIPPING EVENTS

class ShippingAddress(Address):
    """
    A shipping address.

    A shipping address should not be edited once the order has been placed -
    it should be read-only after that.

    NOTE:
    ShippingAddress is a model of the order app. But moving it there is tricky
    due to circular import issues that are amplified by get_model/get_class
    calls pre-Django 1.7 to register receivers. So...
    TODO: Once Django 1.6 support is dropped, move AbstractBillingAddress and
    AbstractShippingAddress to the order app, and move
    PartnerAddress to the partner app.
    """

    phone_number = models.CharField(max_length=20, blank=True, null=True)
    city_id = models.BigIntegerField(_("City Id"), blank=True, null=True)
    notes = models.TextField(
        blank=True, verbose_name=_('Instructions'),
        help_text=_("Tell us anything we should know when delivering "
                    "your order."))

    COURIER, POST_OFFICE = "Courier", "Postoffice"
    TYPE_CHOICES = (
        (COURIER, _(COURIER)),
        (POST_OFFICE, _(POST_OFFICE)),
    )

    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=POST_OFFICE)

    class Meta:
        app_label = 'order'
        verbose_name = _("Shipping address")
        verbose_name_plural = _("Shipping addresses")

    @property
    def order(self):
        """
        Return the order linked to this shipping address
        """
        try:
            return self.order_set.all()[0]
        except IndexError:
            return None


class BillingAddress(Address):
    class Meta:
        app_label = 'order'
        verbose_name = _("Billing address")
        verbose_name_plural = _("Billing addresses")

    @property
    def order(self):
        """
        Return the order linked to this shipping address
        """
        try:
            return self.order_set.all()[0]
        except IndexError:
            return None


class ShippingEvent(models.Model):
    """
    An event is something which happens to a group of lines such as
    1 item being dispatched.
    """
    order = models.ForeignKey(
        'order.Order', related_name='shipping_events', verbose_name=_("Order"))
    lines = models.ManyToManyField(
        'order.Line', related_name='shipping_events',
        through='ShippingEventQuantity', verbose_name=_("Lines"))
    event_type = models.ForeignKey(
        'order.ShippingEventType', verbose_name=_("Event Type"))
    notes = models.TextField(
        _("Event notes"), blank=True,
        help_text=_("This could be the dispatch reference, or a "
                    "tracking number"))
    date_created = models.DateTimeField(_("Date Created"), auto_now_add=True)

    class Meta:
        app_label = 'order'
        verbose_name = _("Shipping Event")
        verbose_name_plural = _("Shipping Events")
        ordering = ['-date_created']

    def __str__(self):
        return _("Order #%(number)s, type %(type)s") % {
            'number': self.order.number,
            'type': self.event_type}

    def num_affected_lines(self):
        return self.lines.count()


class ShippingEventQuantity(models.Model):
    """
    A "through" model linking lines to shipping events.

    This exists to track the quantity of a line that is involved in a
    particular shipping event.
    """
    event = models.ForeignKey(
        'order.ShippingEvent', related_name='line_quantities',
        verbose_name=_("Event"))
    line = models.ForeignKey(
        'order.Line', related_name="shipping_event_quantities",
        verbose_name=_("Line"))
    quantity = models.PositiveIntegerField(_("Quantity"))

    class Meta:
        app_label = 'order'
        verbose_name = _("Shipping Event Quantity")
        verbose_name_plural = _("Shipping Event Quantities")
        unique_together = ('event', 'line')

    def save(self, *args, **kwargs):
        # Default quantity to full quantity of line
        if not self.quantity:
            self.quantity = self.line.quantity
        # Ensure we don't violate quantities constraint
        if not self.line.is_shipping_event_permitted(
                self.event.event_type, self.quantity):
            raise exceptions.InvalidShippingEvent
        super(ShippingEventQuantity, self).save(*args, **kwargs)

    def __str__(self):
        return _("%(product)s - quantity %(qty)d") % {
            'product': self.line.product,
            'qty': self.quantity}


class ShippingEventType(models.Model):
    """
    A type of shipping/fulfillment event

    Eg: 'Shipped', 'Cancelled', 'Returned'
    """
    # Name is the friendly description of an event
    name = models.CharField(_("Name"), max_length=255, unique=True)
    # Code is used in forms
    code = AutoSlugField(_("Code"), max_length=128, unique=True,
                         populate_from='name')

    class Meta:
        # abstract = True
        app_label = 'order'
        verbose_name = _("Shipping Event Type")
        verbose_name_plural = _("Shipping Event Types")
        ordering = ('name',)

    def __str__(self):
        return self.name


# DISCOUNTS


class OrderDiscount(models.Model):
    """
    A discount against an order.

    Normally only used for display purposes so an order can be listed with
    discounts displayed separately even though in reality, the discounts are
    applied at the line level.

    This has evolved to be a slightly misleading class name as this really
    track benefit applications which aren't necessarily discounts.
    """
    order = models.ForeignKey(
        'order.Order', related_name="discounts", verbose_name=_("Order"))

    # We need to distinguish between basket discounts, shipping discounts and
    # 'deferred' discounts.
    BASKET, SHIPPING, DEFERRED = "Basket", "Shipping", "Deferred"
    CATEGORY_CHOICES = (
        (BASKET, _(BASKET)),
        (SHIPPING, _(SHIPPING)),
        (DEFERRED, _(DEFERRED)),
    )
    category = models.CharField(
        _("Discount category"), default=BASKET, max_length=64,
        choices=CATEGORY_CHOICES)

    offer_id = models.PositiveIntegerField(
        _("Offer ID"), blank=True, null=True)
    offer_name = models.CharField(
        _("Offer name"), max_length=128, db_index=True, blank=True)
    voucher_id = models.PositiveIntegerField(
        _("Voucher ID"), blank=True, null=True)
    voucher_code = models.CharField(
        _("Code"), max_length=128, db_index=True, blank=True)
    frequency = models.PositiveIntegerField(_("Frequency"), null=True)
    amount = models.DecimalField(
        _("Amount"), decimal_places=2, max_digits=12, default=0)

    # Post-order offer applications can return a message to indicate what
    # action was taken after the order was placed.
    message = models.TextField(blank=True)

    @property
    def is_basket_discount(self):
        return self.category == self.BASKET

    @property
    def is_shipping_discount(self):
        return self.category == self.SHIPPING

    @property
    def is_post_order_action(self):
        return self.category == self.DEFERRED

    class Meta:
        # abstract = True
        app_label = 'order'
        verbose_name = _("Order Discount")
        verbose_name_plural = _("Order Discounts")

    def save(self, **kwargs):
        if self.offer_id and not self.offer_name:
            offer = self.offer
            if offer:
                self.offer_name = offer.name

        if self.voucher_id and not self.voucher_code:
            voucher = self.voucher
            if voucher:
                self.voucher_code = voucher.code

        super(OrderDiscount, self).save(**kwargs)

    def __str__(self):
        return _("Discount of %(amount)r from order %(order)s") % {
            'amount': self.amount, 'order': self.order}

    @property
    def offer(self):
        Offer = get_model('offer', 'ConditionalOffer')
        try:
            return Offer.objects.get(id=self.offer_id)
        except Offer.DoesNotExist:
            return None

    @property
    def voucher(self):
        Voucher = get_model('voucher', 'Voucher')
        try:
            return Voucher.objects.get(id=self.voucher_id)
        except Voucher.DoesNotExist:
            return None

    def description(self):
        if self.voucher_code:
            return self.voucher_code
        return self.offer_name or ""


class StatusGroup(models.Model):
    name = models.CharField(max_length=64)
    display_name = models.CharField(max_length=64)
    status_class = models.CharField(max_length=70,blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Пользовательский статус'
        verbose_name_plural = 'Пользовательские статусы'


class OrderStatus(models.Model):
    name = models.CharField(
        _("status name"), max_length=128, db_index=True, unique=True)
    display_name = models.CharField(max_length=128, default="")
    group = models.ForeignKey('StatusGroup', null=True, blank=True, related_name='statuses')

    def __str__(self):
        return self.name

    class Meta:
        app_label = 'order'
        verbose_name = _("Статус заказа")
        verbose_name_plural = _("Статусы заказа")


class PaymentStatus(models.Model):
    name = models.CharField(
        _("status name"), max_length=128, db_index=True, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        app_label = 'order'
        verbose_name = _("Order Payment Status")
        verbose_name_plural = _("Order Payment Statuses")


class ShipmentStatus(models.Model):
    name = models.CharField(
        _("status name"), max_length=128, db_index=True, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        app_label = 'order'
        verbose_name = _("Order Shipment Status")
        verbose_name_plural = _("Order Shipment Statuses")


class PaymentType(models.Model):
    name = models.CharField(
        _("payment type name"), max_length=128, db_index=True, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        app_label = 'order'
        verbose_name = _("Типы оплаты")
        verbose_name_plural = _("Типы оплаты")


class ShipmentMethod(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

    class Meta:
        app_label = 'order'
        verbose_name = _("Order Shipment method")
        verbose_name_plural = _("Order Shipment method")


class Spsr_SO_Status(models.Model):
    name = models.CharField(_('Name'), max_length=256)
    status_shop = models.ForeignKey('OrderStatus',
                                    related_name="spsr_so_status",
                                    null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        app_label = 'order'
        verbose_name = _("SPSR Sales Order Status")
        verbose_name_plural = _("SPSR Sales Order Statuses")


class Spsr_PO_Status(models.Model):
    name = models.CharField(_('Name'), max_length=256)
    status_shop = models.ForeignKey('OrderStatus', related_name="spsr_po_status", null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        app_label = 'order'
        verbose_name = _("SPSR Purchase Order Status")
        verbose_name_plural = _("SPSR Purchaseø Order Statuses")


class DoubleProductLine(models.Model):
    order = models.ForeignKey(Order)
    line = models.ForeignKey(Line, related_name='double_product_lines')
    provider = models.ForeignKey(ContractorCatalogue, related_name='contractor_double_product_lines')
    stock = models.PositiveIntegerField()
    price_opt_unit = models.DecimalField(max_digits=10, decimal_places=2)
    price_mrc_unit = models.DecimalField(max_digits=10, decimal_places=2)
    product_contractor = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return str(self.pk)

    class Meta:
        verbose_name = 'Строка заказа для дублей'
        verbose_name_plural = 'Строки заказа для дублей'
