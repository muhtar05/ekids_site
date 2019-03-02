from decimal import Decimal as D

from django.conf import settings
from django.contrib.sites.models import Site
from django.utils.translation import ugettext_lazy as _

from order.models import PaymentStatus, OrderStatus
from basket.models import DeliveryBasket
from partner.models import StockRecord

from . import exceptions

from .models import Order, Line, OrderDiscount
from basket.models import Line as BasketLine
from .signals import order_placed


class OrderNumberGenerator(object):
    """
    Simple object for generating order numbers.

    We need this as the order number is often required for payment
    which takes place before the order model has been created.
    """

    def order_number(self, basket):
        """
        Return an order number for a given basket
        """
        return 100000 + basket.id


class OrderTestCreator(object):
    def place_order(self, basket, total, order_number, **kwargs):
        if basket.is_empty:
            raise ValueError(_("Корзина не должна быть пустой"))
        if not order_number:
            generator = OrderNumberGenerator()
            order_number = generator.order_number(basket)

        status = None
        try:
            Order._default_manager.get(number=order_number)
        except Order.DoesNotExist:
            pass

        # order = self.create_order_model(
        #     user, basket, shipping_address, shipping_charge,
        #     billing_address, total, order_number, status, **kwargs)
        order = None

        for line in basket.all_lines():
            self.create_line_models(order, line)
            self.update_stock_records(order, line)

    def create_order_model(self, user, basket, status, **extra_order_fields):
        pass


class OrderCreator(object):
    """
    Places the order by writing out the various models
    """

    def place_order(self, basket, post_id, order_status, payment_type, total,  # noqa (too complex (12))
                    shipping_charge,promo_discount, user=None,
                    shipping_address=None, billing_address=None,
                    order_number=None, status=None, **kwargs):
        """
        Placing an order involves creating all the relevant models based on the
        basket and session data.
        """
        if basket.is_empty:
            raise ValueError(_("Empty baskets cannot be submitted"))
        if not order_number:
            generator = OrderNumberGenerator()
            order_number = generator.order_number(basket)

        if not status and hasattr(settings, 'OSCAR_INITIAL_ORDER_STATUS'):
            status = getattr(settings, 'OSCAR_INITIAL_ORDER_STATUS')
        try:
            Order._default_manager.get(number=order_number)
        except Order.DoesNotExist:
            pass
        else:
            raise ValueError(_("There is already an order with number %s")
                             % order_number)

        # Ok - everything seems to be in order, let's place the order

        order = self.create_order_model(
            user, basket, post_id, order_status, payment_type, shipping_address, shipping_charge, promo_discount,
            billing_address, total, order_number, status, **kwargs)

        for line in basket.all_lines():
            self.create_line_models(order, line)
            self.update_stock_records(order, line)

        # Отправка письма пользователю
        from django.template.loader import get_template, render_to_string
        from django.core.mail import EmailMultiAlternatives
        ctx = dict()
        discount = order.get_discount_for_order()
        ctx['order'] = order
        ctx['discount'] = int(discount)
        ctx['total_without_shipping'] = order.total_incl_tax - order.shipping_excl_tax
        if order.promo_discount:
            ctx['promo_discount'] = int(order.promo_discount)
        to = order.user.email
        subject, from_email = 'Ваш заказ с сайта ChadoMarket', 'no-reply@chadomarket.ru'
        text_content = render_to_string('mail/order_detail.txt', ctx)
        html_content = get_template('mail/order_detail_new.html').render(ctx)
        msg = EmailMultiAlternatives(subject, html_content, from_email, [to])
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        # Конец

        # Отправка сообщения Косте (Великодушному пожизненному диктатору сайта Chadomarket)
        msg_info = EmailMultiAlternatives("Пришел новый заказ на сайте ChadoMarket", text_content, from_email,
                                          ["kk@chadomarket.ru", "call-center@chadomarket.ru"])
        msg_info.attach_alternative(html_content, "text/html")
        msg_info.send()
        # Конец

        # Record any discounts associated with this order
        for application in basket.offer_applications:
            # Trigger any deferred benefits from offers and capture the
            # resulting message
            application['message'] \
                = application['offer'].apply_deferred_benefit(basket, order,
                                                              application)
            # Record offer application results
            if application['result'].affects_shipping:
                # Skip zero shipping discounts
                shipping_discount = shipping_method.discount(basket)
                if shipping_discount <= D('0.00'):
                    continue
                # If a shipping offer, we need to grab the actual discount off
                # the shipping method instance, which should be wrapped in an
                # OfferDiscount instance.
                application['discount'] = shipping_discount
            self.create_discount_model(order, application)
            self.record_discount(application)

        for voucher in basket.vouchers.all():
            self.record_voucher_usage(order, voucher, user)

        # Send signal for analytics to pick up
        order_placed.send(sender=self, order=order, user=user)

        return order

    def create_order_model(self, user, basket, post_id, order_status,
                           payment_type, shipping_address,
                           shipping_charge, promo_discount, billing_address,
                           total, order_number, status, **extra_order_fields):
        """
        Create an order model.
        """

        total_price = total.excl_tax

        order_data = {'basket': basket,
                      'number': order_number,
                      'currency': total.currency,
                      'total_incl_tax': total.incl_tax,
                      'total_excl_tax': total_price,
                      'shipping_incl_tax': shipping_charge.incl_tax,
                      'shipping_excl_tax': shipping_charge.excl_tax,
                      'promo_discount': promo_discount
                      }

        if payment_type:
            order_data['payment_type'] = payment_type
            if payment_type.pk == 2:
                order_data['payment_status'] = PaymentStatus.objects.get(pk=3)
            else:
                order_data['payment_status'] = PaymentStatus.objects.get(pk=1)

        if billing_address:
            order_data['billing_address'] = billing_address

        if user and user.is_authenticated():
            order_data['user_id'] = user.id
            order_data['phone'] = user.get_main_phone().phone
            order_data['extra_phone'] = user.get_extra_phone()

        if extra_order_fields:
            order_data.update(extra_order_fields)

        delivery_basket = DeliveryBasket.objects.filter(basket=basket).first()
        from checkout.utils import delivery_date_to_time
        try:
            delivery_date = delivery_date_to_time(delivery_basket.delivery_date)
        except Exception as e:
            delivery_date = None

        if delivery_basket:
            order_data['delivery_date'] = delivery_date
            if delivery_basket.delivery_time_interval:
                order_data['delivery_time_interval'] = delivery_basket.delivery_time_interval
            if delivery_basket.post_id:
                order_data['post_id'] = delivery_basket.post_id
            elif delivery_basket.post_id_pick:
                order_data['post_id_pick'] = delivery_basket.post_id_pick
            elif delivery_basket.shipping_address:
                order_data['shipping_address'] = delivery_basket.shipping_address                

        if order_status:
            order_status_supplier = OrderStatus.objects.filter(display_name='request_info_from_supplier').first()
            order_data['status'] = order_status_supplier

        if 'site' not in order_data:
            order_data['site'] = Site._default_manager.get_current()

        order = Order(**order_data)
        order.save()

        return order

    def create_line_models(self, order, basket_line, extra_line_fields=None):
        """
        Create the batch line model.

        You can set extra fields by passing a dictionary as the
        extra_line_fields value
        """
        product = basket_line.product
        stockrecord = basket_line.stockrecord
        if not stockrecord:
            raise exceptions.UnableToPlaceOrder(
                "Baket line #%d has no stockrecord" % basket_line.id)
        partner = stockrecord.partner
        line_data = {
            'order': order,
            # Partner details
            'partner': partner,
            'partner_name': partner.name,
            'partner_sku': stockrecord.partner_sku,
            'stockrecord': stockrecord,
            # Product details
            'product': product,
            'title': product.get_title(),
            'upc': product.upc,
            'quantity': basket_line.quantity,
            # Price details
            'line_price_excl_tax':basket_line.line_price_with_discount,
            'line_price_incl_tax':basket_line.line_price_with_discount,
            'line_price_before_discounts_excl_tax':basket_line.line_price_excl_tax,
            'line_price_before_discounts_incl_tax':basket_line.line_price_incl_tax,
            # Reporting details
            'unit_cost_price': stockrecord.cost_price,
            'unit_opt_price': product.price_opt,
            'unit_price_with_discount': product.get_discount_price(),
            'unit_price_incl_tax': basket_line.unit_price_incl_tax,
            'unit_price_excl_tax': basket_line.unit_price_excl_tax,
            'unit_retail_price': stockrecord.price_retail,
            # Shipping details
            'est_dispatch_date':basket_line.purchase_info.availability.dispatch_date
        }
        extra_line_fields = extra_line_fields or {}
        if hasattr(settings, 'OSCAR_INITIAL_LINE_STATUS'):
            if not (extra_line_fields and 'status' in extra_line_fields):
                extra_line_fields['status'] = getattr(
                    settings, 'OSCAR_INITIAL_LINE_STATUS')
        if extra_line_fields:
            line_data.update(extra_line_fields)

        current_line = Line.objects.filter(order=order, product=product)
        if current_line:
            current_line.update(**line_data)
            order_line = current_line
        else:
            order_line = Line._default_manager.create(**line_data)
            self.create_line_price_models(order, order_line, basket_line)
            self.create_line_attributes(order, order_line, basket_line)
            self.create_additional_line_models(order, order_line, basket_line)

        return order_line

    def update_stock_records(self, order, line):
        """
        Update any relevant stock records for this order line
        """
        order_line = Line.objects.filter(order=order, product=line.product).first()
        if line.product.get_product_class().track_stock:
            chado_stock = StockRecord.objects.filter(product=line.product, is_our_storage=True).first()
            if chado_stock:
                if chado_stock.num_in_stock > chado_stock.num_allocated:
                    num_allow = chado_stock.num_in_stock - chado_stock.num_allocated
                    if num_allow >= line.quantity:
                        chado_stock.allocate(line.quantity)
                        # Добавляем в заказ кол-во товара взятое со склада(для отображения в закупщике)
                        order_line.quantity_from_chado_storage = line.quantity
                        order_line.save()
                    else:
                        chado_stock.allocate(num_allow)
                        stock_rec = StockRecord.objects.filter(product=line.product, is_our_storage=False).first()
                        # Добавляем в заказ кол-во товара взятое со склада(для отображения в закупщике)
                        order_line.quantity_from_chado_storage = num_allow
                        order_line.save()
                        num_last = line.quantity - num_allow
                        stock_rec.allocate(num_last)

                else:
                    stock_rec = StockRecord.objects.filter(product=line.product, is_our_storage=False).first()
                    stock_rec.allocate(line.quantity)
            else:
                line.stockrecord.allocate(line.quantity)

            product = order_line.product
            product.num_allocated += int(line.quantity)
            product.save()

    def create_additional_line_models(self, order, order_line, basket_line):
        """
        Empty method designed to be overridden.

        Some applications require additional information about lines, this
        method provides a clean place to create additional models that
        relate to a given line.
        """
        pass

    def create_line_price_models(self, order, order_line, basket_line):
        """
        Creates the batch line price models
        """
        breakdown = basket_line.get_price_breakdown()
        for price_incl_tax, price_excl_tax, quantity in breakdown:
            order_line.prices.create(
                order=order,
                quantity=quantity,
                price_incl_tax=price_incl_tax,
                price_excl_tax=price_excl_tax)

    def create_line_attributes(self, order, order_line, basket_line):
        """
        Creates the batch line attributes.
        """
        for attr in basket_line.attributes.all():
            order_line.attributes.create(
                option=attr.option,
                type=attr.option.code,
                value=attr.value)

    def create_discount_model(self, order, discount):

        """
        Create an order discount model for each offer application attached to
        the basket.
        """
        order_discount = OrderDiscount(
            order=order,
            message=discount['message'] or '',
            offer_id=discount['offer'].id,
            frequency=discount['freq'],
            amount=discount['discount'])
        result = discount['result']
        if result.affects_shipping:
            order_discount.category = OrderDiscount.SHIPPING
        elif result.affects_post_order:
            order_discount.category = OrderDiscount.DEFERRED
        voucher = discount.get('voucher', None)
        if voucher:
            order_discount.voucher_id = voucher.id
            order_discount.voucher_code = voucher.code
        order_discount.save()

    def record_discount(self, discount):
        discount['offer'].record_usage(discount)
        if 'voucher' in discount and discount['voucher']:
            discount['voucher'].record_discount(discount)

    def record_voucher_usage(self, order, voucher, user):
        """
        Updates the models that care about this voucher.
        """
        voucher.record_usage(order, user)
