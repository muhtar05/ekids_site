import json
import math
from math import ceil
from django import shortcuts
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.template import RequestContext
from django.utils.http import is_safe_url
from django.utils.translation import ugettext_lazy as _
from django.views.generic import FormView, View
from django.contrib.auth import authenticate, login
from django.views.generic import TemplateView, View
from django.conf import settings
from django.template.loader import get_template, render_to_string
from django.core.mail import EmailMultiAlternatives
from django.middleware import csrf
from django.utils import timezone

from extra_views import ModelFormSetView

from address.forms import UserPostAddressCreateForm
from logistics_exchange.cart_tariff_calculate import Calc
from core import ajax
from core.loading import get_model
from core.utils import redirect_to_referrer, safe_referrer

from shipping.repository import Repository
from logistics_exchange.models import City
from order.models import Order
from checkout.calculators import OrderTotalCalculator
from basket.utils import BasketMessageGenerator
from address.models import UserAddress

from catalogue.serializers import get_date_format
from catalogue.models import Product, ProductAttributeValue
from catalogue.serializers import get_pvz_and_apt, get_subway
from common.context_processors import geo_city
from common.forms import CustomCheckoutRegisterFormFromBasket
from customer.models import User, PhoneUser

from . import signals
from .forms import (
    BasketLineFormSet, BasketLineForm,
    AddToBasketForm, BasketVoucherForm,
    SavedLineForm, SavedLineFormSet,
)
from .models import Line, Basket, StockReserve, OldReserveLine


class BasketView(ModelFormSetView):
    model = Line
    basket_model = Basket
    formset_class = BasketLineFormSet
    form_class = BasketLineForm
    extra = 0
    can_delete = True
    template_name = 'basket/basket.html'

    def get_formset_kwargs(self):
        kwargs = super().get_formset_kwargs()
        kwargs['strategy'] = self.request.strategy
        return kwargs

    def get_queryset(self):
        return self.request.basket.all_lines()

    def get_shipping_methods(self, basket):
        return Repository().get_shipping_methods(
            basket=self.request.basket, user=self.request.user,
            request=self.request)

    def get_default_shipping_method(self, basket):
        return Repository().get_default_shipping_method(
            basket=self.request.basket, user=self.request.user,
            request=self.request)

    def get_basket_warnings(self, basket):
        warnings = []
        for line in basket.all_lines():
            warning = line.get_warning()
            if warning:
                warnings.append(warning)
        return warnings

    def get_basket_voucher_form(self):
        return BasketVoucherForm()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated():
            context['user_address_form'] = UserPostAddressCreateForm(user=self.request.user)
        context['current_basket'] = self.request.basket
        context['voucher_form'] = self.get_basket_voucher_form()
        context['shipping_methods'] = self.get_shipping_methods(self.request.basket)
        method = self.get_default_shipping_method(self.request.basket)
        context['shipping_method'] = method
        shipping_charge = method.calculate(self.request.basket)
        context['shipping_charge'] = shipping_charge

        # Берем временные интервалы
        order_class = Order()
        time_choises = order_class.INTERVALS_VARIANTS
        context['time_choises'] = time_choises

        if method.is_discounted:
            excl_discount = method.calculate_excl_discount(self.request.basket)
            context['shipping_charge_excl_discount'] = excl_discount
        order_total = OrderTotalCalculator().calculate(self.request.basket, shipping_charge)
        context['order_total'] = order_total
        discount_total, total_price, total_weight = 0, 0, 0

        basket_product_ids = []
        for l in self.request.basket.lines.all():
            basket_product_ids.append(str("'" + str(l.product.id) + "'"))
            active_discount = l.product.get_active_discount()
            line_total = l.unit_price_excl_tax * l.quantity

            total_price += l.line_price_excl_tax
            product_att = ProductAttributeValue.objects.filter(
                attribute__code__in=['weight', 'ind_weight'], product=l.product)
            if product_att.filter(attribute__code='ind_weight'):
                weight = product_att.get(attribute__code='ind_weight').value_float
            elif product_att.filter(attribute__code='weight'):
                weight = product_att.get(attribute__code='weight').value_float
            else:
                weight = 300
            total_weight += weight * l.quantity

        discount_total += round(order_total.incl_tax - order_total.excl_tax)

        basket_product_ids_to_string = ','.join(basket_product_ids)
        basket_product_ids_strring = '[' + basket_product_ids_to_string + ']'

        context['discount_total'] = discount_total
        context['total_weight'] = total_weight
        context['discount_order_total'] = total_price - discount_total
        context['basket_warnings'] = self.get_basket_warnings(self.request.basket)
        context['YANDEX_MONEY'] = settings.YANDEX_MONEY
        context['basket_product_ids'] = basket_product_ids_strring

        basket_products = Product.objects.filter(id__in=self.request.basket.lines.values('product_id'))
        if self.request.user.is_authenticated():
            first_order = 0 if Order.objects.filter(user=self.request.user).count() > 0 else 1
        else:
            first_order = 1

        OldReserveLine.objects.filter(is_show=True, basket=self.request.basket).update(is_show=False)

        #Время прошло,обратно ставим в резерв
        if StockReserve.objects.filter(line__basket__id=self.request.basket.pk, is_active=False).exists():
            for l in self.request.basket.lines.all():
                product_line = l.product
                if l.product.num_in_stock > 0 and l.product.num_in_stock > l.product.num_allocated:
                    actual_quantity = l.product.num_in_stock - l.product.num_allocated
                    current_quantity = l.quantity
                    stock_reserve_line = l.stock_reserve_lines.first()
                    stock_reserve_line.start_reserve = timezone.now()
                    stock_reserve_line.end_reserve = timezone.now() + timezone.timedelta(minutes=10)
                    stock_reserve_line.is_active = True
                    stock_reserve_line.save()
                    if current_quantity >= actual_quantity:
                        quantity = actual_quantity
                        l.quantity = quantity
                        l.save()
                    else:
                        quantity = current_quantity

                    product_line.num_allocated += quantity
                    product_line.save()
                    stockrecord = product_line.stockrecords.first()
                    stockrecord.num_allocated += quantity
                    stockrecord.save()
                else:
                    old_reverse = OldReserveLine()
                    old_reverse.basket = l.basket
                    old_reverse.product = l.product
                    old_reverse.quantity = l.quantity
                    old_reverse.price_excl_tax = l.price_excl_tax
                    old_reverse.price_incl_tax = l.price_incl_tax
                    old_reverse.is_show = True
                    old_reverse.line_id = l.pk
                    old_reverse.save()
                    Line.objects.get(pk=l.pk).delete()

        stock_reserved = StockReserve.objects.filter(line__basket__id=self.request.basket.pk, is_active=True)
        if stock_reserved:
            end_reserve = stock_reserved.first().end_reserve
            print("end reserve",end_reserve)
            timer = end_reserve - timezone.now()
            timer = math.ceil(timer.total_seconds()) if timer.total_seconds() > 0 else 0
            context['timer'] = timer

        city = geo_city(self.request)['city_data']
        if city:
            city_id = city.city_id
            try:
                results = get_pvz_and_apt(basket_products, city_id)
            except:
                results = ''
            if results != '':
                context['day_for_free_delivery'] = get_date_format(1, city_id)
                context['offices_bool'] = results['offices_bool']
                context['offices_check'] = results['offices_check']
            context['first_order'] = first_order
            context['city'] = city

        if self.request.user.is_authenticated():
            users_address = UserAddress._default_manager.filter(user=self.request.user)
            context['users_address'] = users_address
            try:
                saved_basket = self.basket_model.saved.get(owner=self.request.user)
            except self.basket_model.DoesNotExist:
                pass
            else:
                saved_basket.strategy = self.request.basket.strategy
                if not saved_basket.is_empty:
                    saved_queryset = saved_basket.all_lines()
                    formset = SavedLineFormSet(strategy=self.request.strategy,
                                               basket=self.request.basket,
                                               queryset=saved_queryset,
                                               prefix='saved')
                    context['saved_formset'] = formset

        old_lines_ids = OldReserveLine.objects.values_list('line_id', flat=True).filter(basket=self.request.basket.pk)
        context['old_lines_ids'] = old_lines_ids
        return context

    def get_success_url(self):
        return safe_referrer(self.request, 'basket:summary')

    def formset_valid(self, formset):
        offers_before = self.request.basket.applied_offers()
        save_for_later = False
        flash_messages = ajax.FlashMessages()
        # import code; code.interact(local=dict(globals(), **locals()))
        for form in formset:
            if (hasattr(form, 'cleaned_data') and
                    form.cleaned_data['save_for_later']):
                line = form.instance
                if self.request.user.is_authenticated():
                    self.move_line_to_saved_basket(line)
                    msg = render_to_string(
                        'basket/messages/line_saved.html',
                        {'line': line})
                    flash_messages.info(msg)
                    save_for_later = True
                else:
                    msg = _("You can't save an item for later if you're "
                            "not logged in!")
                    flash_messages.error(msg)
                    return redirect(self.get_success_url())

        if save_for_later:
            response = redirect(self.get_success_url())
        else:
            response = super().formset_valid(formset)
        BasketMessageGenerator().apply_messages(self.request, offers_before)
        return response

    def json_response(self, ctx, flash_messages):
        basket_html = render_to_string(
            'basket/partials/basket_content.html',
            RequestContext(self.request, ctx))
        payload = {
            'content_html': basket_html,
            'messages': flash_messages.as_dict()}
        return HttpResponse(json.dumps(payload),
                            content_type="application/json")

    def move_line_to_saved_basket(self, line):
        saved_basket, _ = get_model('basket', 'basket').saved.get_or_create(owner=self.request.user)
        saved_basket.merge_line(line)

    def formset_invalid(self, formset):
        flash_messages = ajax.FlashMessages()
        flash_messages.warning(_(
            "Your basket couldn't be updated. "
            "Please correct any validation errors below."))

        if self.request.is_ajax():
            ctx = self.get_context_data(formset=formset,
                                        basket=self.request.basket)
            return self.json_response(ctx, flash_messages)

        flash_messages.apply_to_request(self.request)
        return super().formset_invalid(formset)


class BasketAddView(FormView):
    """
    Handles the add-to-basket submissions, which are triggered from various
    parts of the site. The add-to-basket form is loaded into templates using
    a templatetag from module basket_tags.py.
    """
    form_class = AddToBasketForm
    product_model = get_model('catalogue', 'product')
    add_signal = signals.basket_addition
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        self.product = shortcuts.get_object_or_404(
            self.product_model, pk=kwargs['pk'])
        print(self.product)
        return super().post(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['basket'] = self.request.basket
        kwargs['product'] = self.product
        return kwargs

    def form_invalid(self, form):
        print("form_invalid")
        # import code; code.interact(local=dict(globals(), **locals()))
        msgs = []
        for error in form.errors.values():
            msgs.append(error.as_text())
        clean_msgs = [m.replace('* ', '') for m in msgs if m.startswith('* ')]
        # messages.error(self.request, ",".join(clean_msgs))
        data = {'status': 'error', 'errors': ",".join(clean_msgs)}
        return HttpResponse(json.dumps(data), content_type='application/json')

    def form_valid(self, form):
        offers_before = self.request.basket.applied_offers()
        current_line,created  = self.request.basket.add_product(
            form.product, form.cleaned_data['quantity'],
            form.cleaned_options())

        # Send signal for basket addition
        self.add_signal.send(
            sender=self, product=form.product, user=self.request.user,
            request=self.request)

        method = self.get_default_shipping_method(self.request.basket)
        shipping_charge = method.calculate(self.request.basket)
        result = OrderTotalCalculator().calculate(
            self.request.basket, shipping_charge)

        data = {'excl_tax': int(float(result.excl_tax)),
                'incl_tax': int(float(result.incl_tax)),
                'num_items': self.request.basket.num_items,
                'status': 'ok',
                }

        data = json.dumps(data)
        return HttpResponse(data, content_type='application/json')

    def get_default_shipping_method(self, basket):
        return Repository().get_default_shipping_method(
            basket=self.request.basket, user=self.request.user,
            request=self.request)

    def get_success_message(self, form):
        return render_to_string(
            'basket/messages/addition.html',
            {'product': form.product,
             'quantity': form.cleaned_data['quantity']})

    def get_success_url(self):
        post_url = self.request.POST.get('next')
        if post_url and is_safe_url(post_url, self.request.get_host()):
            return post_url
        return safe_referrer(self.request, 'basket:summary')


class SavedView(ModelFormSetView):
    model = Line
    basket_model = Basket
    formset_class = SavedLineFormSet
    form_class = SavedLineForm
    extra = 0
    can_delete = True

    def get(self, request, *args, **kwargs):
        return redirect('basket:summary')

    def get_queryset(self):
        try:
            saved_basket = self.basket_model.saved.get(owner=self.request.user)
            saved_basket.strategy = self.request.strategy
            return saved_basket.all_lines()
        except self.basket_model.DoesNotExist:
            return []

    def get_success_url(self):
        return safe_referrer(self.request, 'basket:summary')

    def get_formset_kwargs(self):
        kwargs = super().get_formset_kwargs()
        kwargs['prefix'] = 'saved'
        kwargs['basket'] = self.request.basket
        kwargs['strategy'] = self.request.strategy
        return kwargs

    def formset_valid(self, formset):
        offers_before = self.request.basket.applied_offers()
        is_move = False
        for form in formset:
            if form.cleaned_data.get('move_to_basket', False):
                is_move = True
                msg = render_to_string(
                    'basket/messages/line_restored.html',
                    {'line': form.instance})
                messages.info(self.request, msg, extra_tags='safe noicon')
                real_basket = self.request.basket
                real_basket.merge_line(form.instance)

        if is_move:
            BasketMessageGenerator().apply_messages(self.request, offers_before)
            response = redirect(self.get_success_url())
        else:
            response = super().formset_valid(formset)
        return response

    def formset_invalid(self, formset):
        messages.error(
            self.request,
            '\n'.join(
                error for ed in formset.errors for el
                in ed.values() for error in el))
        return redirect_to_referrer(self.request, 'basket:summary')


class BasketMethods(object):
    def pvz_array_for_ajax(self, results_pvz_apt):
        if results_pvz_apt:
            result_pvz, result_apt = [], []
            if results_pvz_apt['offices_pvz']:
                for pvz in results_pvz_apt['offices_pvz']:
                    address = str(pvz.street_abbr) + ' ' + str(pvz.street) + ', ' + str(pvz.house)
                    if pvz.building:
                        address += ',стр. ' + str(pvz.building)
                    diction = {
                        'address': address,
                        'work_time': pvz.delivery_schedule,
                        'pk': pvz.pk,
                        'type_title': "ПВП",
                        'city_name': pvz.city_name,
                        'subway': pvz.subway,
                        'npp': 1 if pvz.is_npp else 0,
                        'type': 's'
                    }
                    result_pvz.append(diction)
            if results_pvz_apt['offices_pick_pvz']:
                for pvz in results_pvz_apt['offices_pick_pvz']:
                    address = str(pvz.street_abbr) + ' ' + str(pvz.street) + ', ' + str(pvz.house)
                    if pvz.building:
                        address += ',стр. ' + str(pvz.building)
                    diction = {
                        'address': address,
                        'descript': pvz.descript,
                        'work_time': pvz.delivery_schedule,
                        'pk': pvz.pk,
                        'type_title': pvz.type_title,
                        'city_name': pvz.city_name,
                        'subway': pvz.subway,
                        'npp': 1 if pvz.is_npp else 0,
                        'type': 'p'
                    }
                    result_pvz.append(diction)

            if results_pvz_apt['offices_pick_apt']:
                for apt in results_pvz_apt['offices_pick_apt']:
                    address = str(apt.street_abbr) + ' ' + str(apt.street) + ', ' + str(apt.house)
                    if apt.building:
                        address += ',стр. ' + str(apt.building)
                    diction = {
                        'address': address,
                        'descript': apt.descript,
                        'work_time': apt.delivery_schedule,
                        'pk': apt.pk,
                        'type_title': apt.type_title,
                        'city_name': apt.city_name,
                        'subway': apt.subway,
                        'npp': 1 if apt.is_npp else 0,
                        'type': 'p'
                    }
                    result_apt.append(diction)

            return {'result_pvz': result_pvz,
                    'result_apt': result_apt}
        else:
            return {'result_pvz': [],
                    'result_apt': []}


class AddPvzAptAjax(BasketMethods, View):

    def get(self, request, *args, **kwargs):
        city_object = geo_city(self.request)['city_data']
        if city_object:
            products = []
            for line in self.request.basket.lines.all():
                products.append(line.product)
            try:
                results_pvz_apt = get_pvz_and_apt(products, city_object.city_id)
            except:
                results_pvz_apt = None

            subways = get_subway(results_pvz_apt)
            if results_pvz_apt:
                if results_pvz_apt.get('offices_pvz') or results_pvz_apt.get('offices_pick_pvz'):
                    enable_pvz = 1
                else:
                    enable_pvz = 0
                enable_apt = 1 if results_pvz_apt.get('offices_pick_apt') else 0
                array_results = self.pvz_array_for_ajax(results_pvz_apt)
                result_pvz = array_results.get('result_pvz')
                result_apt = array_results.get('result_apt')
                data = {
                    'result_pvz': result_pvz,
                    'result_apt': result_apt,
                    'offices_check': results_pvz_apt['offices_check'],
                    'subway': subways,
                    'enable_pvz': enable_pvz,
                    'enable_apt': enable_apt
                }
            else:
                data = {
                    'result_pvz': None,
                    'result_apt': None,
                    'offices_check': None,
                    'subway': None,
                    'enable_pvz': None,
                    'enable_apt': None
                }
            data = json.dumps(data)
            return HttpResponse(data, content_type='application/json')


class RemoveBasketLine(BasketMethods, View):
    """
    Удаление товаров в корзине. Запрос приходит в качестве ajax-запроса
    """
    def get(self, request, *args, **kwargs):
        pk = kwargs.get('pk', None)
        if pk:
            remove_line = Line.objects.filter(pk=pk).first()
            check_product = remove_line.product
            quantity = remove_line.quantity
            Line.objects.filter(pk=pk).delete()
            check_product.num_allocated -= quantity
            if check_product.num_allocated < 1:
                check_product.num_allocated = 0
            check_product.save()
            stockrecord = check_product.stockrecords.first()
            stockrecord.num_allocated -= quantity
            if stockrecord.num_allocated < 1:
                stockrecord.num_allocated = 0
            stockrecord.save()

        city_object = geo_city(self.request)['city_data']
        products_quantity = 0
        if city_object:
            products = []
            for line in self.request.basket.lines.all():
                products.append(line.product)
                products_quantity += line.quantity
            try:
                results_pvz_apt = get_pvz_and_apt(products, city_object.city_id)
            except:
                results_pvz_apt = dict()
            enable_pvz = 1 if results_pvz_apt.get('offices_pvz') or results_pvz_apt.get('offices_pick_pvz') else 0
            enable_apt = 1 if results_pvz_apt.get('offices_pick_apt') else 0
        else:
            results_pvz_apt = dict()

        subways = get_subway(results_pvz_apt)
        array_results = self.pvz_array_for_ajax(results_pvz_apt)
        result_pvz,result_apt = [],[]
        if array_results['result_pvz']:
            result_pvz = array_results.get('result_pvz')
        if array_results['result_apt']:
            result_apt = array_results.get('result_apt')

        method = self.get_default_shipping_method(self.request.basket)
        shipping_charge = method.calculate(self.request.basket)
        result = OrderTotalCalculator().calculate(self.request.basket, shipping_charge)

        data = {
            'excl_tax': int(float(result.excl_tax)),
            'incl_tax': int(float(result.incl_tax)),
            'result_pvz': result_pvz,
            'result_apt': result_apt,
            'offices_check': results_pvz_apt['offices_check'],
            'subway': subways,
            'enable_pvz': enable_pvz,
            'enable_apt': enable_apt,
            'num_items': products_quantity
        }
        data = json.dumps(data)
        return HttpResponse(data, content_type='application/json')

    def get_default_shipping_method(self, basket):
        return Repository().get_default_shipping_method(
            basket=self.request.basket, user=self.request.user,
            request=self.request)


class ChangeQuantity(View):
    """
     Изменение количество заказываемых товаров в корзине
    """
    def get_default_shipping_method(self, basket):
        return Repository().get_default_shipping_method(
            basket=self.request.basket, user=self.request.user,
            request=self.request)

    def post(self, request, *args, **kwargs):
        if request.is_ajax():
            print("=====POST=====")
            print(request.POST)
            pk = kwargs.get('pk')
            quantity = request.POST.get('value', 0)
            quantity = int(quantity)
            line = Line.objects.filter(pk=pk, basket=request.basket).first()
            current_quantity = line.quantity
            product = line.product
            actual_stock = product.num_in_stock - product.num_allocated

            if quantity >= actual_stock + current_quantity:
                quantity = actual_stock + current_quantity

            sub_quantity = quantity - current_quantity
            product.num_allocated += sub_quantity

            stockrecord = product.stockrecords.first()
            stockrecord.num_allocated += sub_quantity
            stockrecord.save()
            product.save()

            Line.objects.filter(pk=pk, basket=request.basket).update(quantity=quantity)
            method = self.get_default_shipping_method(self.request.basket)
            shipping_charge = method.calculate(self.request.basket)
            result = OrderTotalCalculator().calculate(self.request.basket, shipping_charge)
            data = {
                'total_discount': int(float(result.discount)),
                'total_order_price': int(float(result.excl_tax)),
                'excl_tax': int(float(result.excl_tax)),
                'num_items': self.request.basket.num_items,
                'val': quantity,
                'actual_stock': product.num_in_stock  - product.num_allocated,
                'status': 'ok',
            }
            return HttpResponse(json.dumps(data), content_type='application/json')
        else:
            data = {'status': 'This is not ajax'}
            return HttpResponse(json.dumps(data), content_type='application/json')


class SpsrDeliveryData(object):
    def get_price(self, lines):
        price = 0
        for line in lines:
            product_price = line.get('price_mrc', 0)
            all_product_price_1 = product_price * line.get('quantity')
            price += all_product_price_1

        return {
            'price': price,
        }

    def get_courier_info(self, price, products_lines, city):
        quantity = dict()
        product_ids = []
        for pr in products_lines:
            product_ids.append(pr['product_id'])
            quantity[pr['product_id']] = pr['quantity']
        if city:
            product_att = ProductAttributeValue.objects.filter(
                attribute__code__in=['weight', 'ind_weight', 'ind_length', 'length', 'ind_width', 'width', 'ind_height',
                                     'height'], product__id__in=product_ids)

        if str(city.city_id) == '49694102':
            lower_time_array = settings.ADDITIONAL_DAYS
            lptime_courier = get_date_format(lower_time_array, city.city_id)
            if int(price) >= settings.ORDER_SUM_FOR_FREE_SHIP:
                min_price_courier = 'Бесплатно'
            else:
                min_price_courier = 300
        else:
            delivery_courier = Calc(city, [product_att], quantity, 'curier')
            min_price_courier = ceil(delivery_courier.min_price)
            lower_time_array_courier = str(delivery_courier.lowest_price_time).split('-')
            lptime_courier = get_date_format(lower_time_array_courier, city.city_id)

        if min_price_courier is str:
            data = {
                'min_price_courier': int(round(float(min_price_courier))),
                'lowest_time_courier': lptime_courier,
            }
        else:
            data = {
                'min_price_courier': min_price_courier,
                'lowest_time_courier': lptime_courier,
            }
        return data

    def get_result(self, input_data):
        min_price = input_data.get('min_price')
        lptime = input_data.get('lptime')
        min_price_courier = input_data.get('min_price_courier')
        lptime_courier = input_data.get('lptime_courier')
        min_price_pvz = input_data.get('min_price_pvz')
        lptime_pvz = input_data.get('lptime_pvz')
        if min_price is str:
            data = {
                'min_price': int(round(float(min_price))),
                'lowest_time': lptime,
                'min_price_courier': int(round(float(min_price_courier))),
                'lowest_time_courier': lptime_courier,
                'min_price_pvz': int(round(float(min_price_pvz))),
                'lowest_time_pvz': lptime_pvz
            }
        else:
            data = {
                'min_price': min_price,
                'lowest_time': lptime,
                'min_price_courier': min_price_courier,
                'lowest_time_courier': lptime_courier,
                'min_price_pvz': min_price_pvz,
                'lowest_time_pvz': lptime_pvz
            }
        return data

    def get_info_all_russia(self):
        return {
            'min_price': 0,
            'min_price_pvz': 0,
            'min_price_courier': 0,
            'lptime': 0,
            'lptime_pvz': 0,
            'lptime_courier': 0
        }


def get_spsr_info(price, products_lines, city):
    quantity = dict()
    product_ids = []
    for pr in products_lines:
        product_ids.append(pr['product_id'])
        quantity[pr['product_id']] = pr['quantity']
    if city:
        product_att = []
        for product_id in product_ids:
            product_att_temp = ProductAttributeValue.objects.filter(
                attribute__code__in=['weight', 'ind_weight', 'ind_length', 'length', 'ind_width', 'width',
                                     'ind_height', 'height'], product__id=product_id)
            product_att.append(product_att_temp)

        print('product_att === ', product_att)

        if str(city.city_id) == '49694102':
            lower_time_array = settings.ADDITIONAL_DAYS
            lptime = lptime_pvz = lptime_courier = get_date_format(lower_time_array, city.city_id)
            if int(price) >= settings.ORDER_SUM_FOR_FREE_SHIP:
                min_price = min_price_pvz = min_price_courier = 'Бесплатно'
            else:
                min_price = min_price_pvz = min_price_courier = '300'

        else:
            delivery = Calc(city, product_att, quantity, 'curier')
            delivery_pvz = Calc(city, product_att, quantity, 'pvz')

            if delivery.min_price:
                print('delivery.min_price === ', delivery.min_price)
                min_price_courier = ceil(float(delivery.min_price))
            else:
                min_price_courier = None
            if delivery.lowest_price_time:
                print('delivery.lowest_price_time === ', delivery.lowest_price_time)
                lptime_courier = get_date_format(delivery.lowest_price_time, city.city_id)
            else:
                lptime_courier = None

            if delivery_pvz.min_price:
                print('delivery_pvz.min_price === ', delivery_pvz.min_price)
                min_price = min_price_pvz = ceil(float(delivery_pvz.min_price))
            else:
                min_price = min_price_pvz = None
            if delivery_pvz.lowest_price_time:
                print('delivery_pvz.lowest_price_time === ', delivery_pvz.lowest_price_time)
                lptime = lptime_pvz = get_date_format(delivery_pvz.lowest_price_time, city.city_id)
            else:
                lptime = lptime_pvz = None

    else:
        min_price = None
        min_price_courier = None
        min_price_pvz = None
        lptime = None
        lptime_courier = None
        lptime_pvz = None

    return {
        'min_price': min_price,
        'min_price_courier': min_price_courier,
        'min_price_pvz': min_price_pvz,
        'lowest_time': lptime,
        'lptime_courier': lptime_courier,
        'lptime_pvz': lptime_pvz,
    }


class SpsrDataView(SpsrDeliveryData, View):
    def get(self, request, *args, **kwargs):
            city = geo_city(request)['city_data']
            if not city:
                data = {'error': True,
                        'message': 'В ' + city.city_name + ' невозможно доставить заказ'
                        }
                return HttpResponse(json.dumps(data), content_type='application/json')

            lines = request.basket.lines.all()
            lines_data = []
            spsr_info = {}
            for line in lines:
                current_prod = Product.objects.get(pk=int(line.product.pk))
                product_att = ProductAttributeValue.objects.filter(
                    attribute__code__in=['weight', 'ind_weight'], product__id=line.product.pk)
                weight = product_att.get(attribute__code='ind_weight').value_float or product_att.get(
                    attribute__code='weight').value_float
                current_quantity = int(line.quantity)
                lines_data.append({'weight': weight,
                                   'price_mrc': current_prod.price_mrc,
                                   'quantity': current_quantity,
                                   'product_id': current_prod.id})
            product_data = self.get_price(lines_data)
            price = product_data.get('price')
            if str(city.city_id) == '49694102':
                lower_time_array = settings.ADDITIONAL_DAYS
                spsr_info['lptime'] = spsr_info['lptime_courier'] = spsr_info['lptime_pvz'] = get_date_format(
                    lower_time_array, city.city_id)
                if int(price) >= settings.ORDER_SUM_FOR_FREE_SHIP:
                    spsr_info['min_price'] = spsr_info['min_price_pvz'] = spsr_info['min_price_courier'] = 'Бесплатно'
                else:
                    spsr_info['min_price'] = spsr_info['min_price_pvz'] = spsr_info['min_price_courier'] = '300'

            else:
                spsr_info = get_spsr_info(price, lines_data, city)
            data = self.get_result(spsr_info)
            return HttpResponse(json.dumps(data), content_type='application/json')


class SpsrCourierDeliveryView(SpsrDeliveryData, View):
    def get(self, request, *args, **kwargs):
        lines = request.basket.lines.all()
        for l in lines:
            product_att = ProductAttributeValue.objects.filter(
                attribute__code__in=['weight', 'ind_weight'], product=l.product)
            weight = product_att.get(attribute__code='ind_weight').value_float or product_att.get(
                attribute__code='weight').value_float
            lines_data = [{'weight': weight,
                           'price_mrc': l.product.price_mrc,
                           'quantity': l.quantity,
                           'product_id': l.product.id}]
        product_data = self.get_price(lines_data)
        city = geo_city(request)['city_data']
        price = product_data.get('price')
        spsr_info = self.get_courier_info(price, lines_data, city)
        data = spsr_info
        return HttpResponse(json.dumps(data), content_type='application/json')


class SpsrCallCentrDeliveryView(SpsrDeliveryData, View):
    """Получение стоимости доставки от DPD для заказа в call center"""

    def post(self, request, *args, **kwargs):
        city_name = request.POST.get('city_name')
        city_id = request.POST.get('city_id')
        city = City.objects.filter(city_id=city_id).first()
        print('city ====== ', city)
        if not city:
            data = {'error': True,
                    'message': 'В ' + city_name + ' невозможно доставить заказ'
                    }
            return HttpResponse(json.dumps(data), content_type='application/json')
        products = request.POST.getlist('products[]')
        stocks = request.POST.getlist('stocks[]')
        lines = list(zip(products, stocks))
        lines_data = []
        spsr_info = {}
        for line in lines:
            current_prod = Product.objects.get(pk=int(line[0]))
            product_att = ProductAttributeValue.objects.filter(
                attribute__code__in=['weight', 'ind_weight'], product__id=line[0])
            weight = product_att.get(attribute__code='ind_weight').value_float or product_att.get(
                attribute__code='weight').value_float
            current_quantity = int(line[1])
            lines_data.append({'weight': weight,
                               'price_mrc': current_prod.price_mrc,
                               'quantity': current_quantity,
                               'product_id': current_prod.id})
        product_data = self.get_price(lines_data)
        price = product_data.get('price')
        if str(city.city_id) == '49694102':
            lower_time_array = settings.ADDITIONAL_DAYS
            spsr_info['lptime'] = spsr_info['lptime_courier'] = spsr_info['lptime_pvz'] = get_date_format(lower_time_array, city.city_id)
            if int(price) >= settings.ORDER_SUM_FOR_FREE_SHIP:
                spsr_info['min_price'] = spsr_info['min_price_pvz'] = spsr_info['min_price_courier'] = 'Бесплатно'
            else:
                spsr_info['min_price'] = spsr_info['min_price_pvz'] = spsr_info['min_price_courier'] = '300'

        else:
            spsr_info = get_spsr_info(price, lines_data, city)
        data = self.get_result(spsr_info)
        return HttpResponse(json.dumps(data), content_type='application/json')


def get_spsr_delivery_data(request):
    if geo_city(request)['city_data']:
        city = geo_city(request)['city_data']
        products_lines = request.basket.lines.all()
        product_ids = []
        quantity = dict()
        price = 0
        for pr in products_lines:
            product_ids.append(pr['product_id'])
            quantity[pr['product_id']] = pr['quantity']
            product_price = pr.get('price_mrc', 0)
            all_product_price_1 = product_price * pr.get('quantity')
            price += all_product_price_1

        if city:
            product_att = ProductAttributeValue.objects.filter(
                attribute__code__in=['weight', 'ind_weight', 'ind_length', 'length', 'ind_width', 'width', 'ind_height',
                                     'height'], product__in=product_ids)
            if str(city.city_id) == '49694102':
                lower_time_array = settings.ADDITIONAL_DAYS
                lptime = lptime_courier = lptime_pvz = get_date_format(lower_time_array, city.city_id)
                if int(price) >= settings.ORDER_SUM_FOR_FREE_SHIP:
                    min_price = min_price_pvz = min_price_courier = 'Бесплатно'
                else:
                    min_price = min_price_pvz = min_price_courier = '300'

            else:
                delivery = Calc(city, [product_att], quantity, 'curier')
                delivery_pvz = Calc(city, [product_att], quantity, 'pvz')
                if delivery.min_price:
                    print('delivery.min_price === ', delivery.min_price)
                    min_price_courier = ceil(float(delivery.min_price))
                else:
                    min_price_courier = None
                if delivery.lowest_price_time:
                    print('delivery.lowest_price_time === ', delivery.lowest_price_time)
                    lptime_courier = get_date_format(delivery.lowest_price_time, city.city_id)
                else:
                    lptime_courier = None

                if delivery_pvz.min_price:
                    print('delivery_pvz.min_price === ', delivery_pvz.min_price)
                    min_price = min_price_pvz = ceil(float(delivery_pvz.min_price))
                else:
                    min_price = min_price_pvz = None
                if delivery_pvz.lowest_price_time:
                    print('delivery_pvz.lowest_price_time === ', delivery_pvz.lowest_price_time)
                    lptime = lptime_pvz = get_date_format(delivery_pvz.lowest_price_time, city.city_id)
                else:
                    lptime = lptime_pvz = None

    else:
        min_price = None
        min_price_courier = None
        min_price_pvz = None
        lptime = None
        lptime_courier = None
        lptime_pvz = None

    data = {
        'min_price': min_price,
        'lowest_time': lptime,
        'min_price_courier': min_price_courier,
        'lowest_time_courier': lptime_courier,
        'min_price_pvz': min_price_pvz,
        'lowest_time_pvz': lptime_pvz,
    }

    return HttpResponse(json.dumps(data), content_type='application/json')


def get_courier_delivery_date(request):
    city_id = request.POST.get('city_id')
    city_name = request.POST.get('city_name')
    if city_id != 'None':
        city = City.objects.filter(city_id=int(city_id)).first()
    else:
        city = None

    if not city:
        city = City.objects.filter(city_name=city_name).first()

    products_lines = request.basket.lines.all()
    product_ids = []
    quantity = dict()
    price = 0
    for pr in products_lines:
        product_ids.append(pr.product.id)
        quantity[pr.product.id] = pr.quantity
        product_price = pr.product.price_mrc or 0
        all_product_price_1 = product_price * pr.quantity
        price += all_product_price_1

    if city:
        product_att = ProductAttributeValue.objects.filter(
            attribute__code__in=['weight', 'ind_weight', 'ind_length', 'length', 'ind_width', 'width', 'ind_height',
                                 'height'], product__in=product_ids)
        if str(city.city_id) == '49694102':
            lower_time_array = settings.ADDITIONAL_DAYS
            lptime = lptime_courier = get_date_format(lower_time_array, city.city_id)
            if int(price) >= settings.ORDER_SUM_FOR_FREE_SHIP:
                min_price = min_price_courier = 'Бесплатно'
            else:
                min_price = min_price_courier = '300'
        else:
            delivery = Calc(city, [product_att], quantity, 'curier')
            if delivery.min_price:
                print('delivery.min_price === ', delivery.min_price)
                min_price_courier = ceil(float(delivery.min_price))
            else:
                min_price_courier = None
            if delivery.lowest_price_time:
                print('delivery.lowest_price_time === ', delivery.lowest_price_time)
                lptime_courier = get_date_format(delivery.lowest_price_time, city.city_id)
            else:
                lptime_courier = None

    else:
        min_price_courier = None
        lptime_courier = None

    data = {
        'min_price_courier': min_price_courier,
        'lowest_time_courier': lptime_courier,
    }

    return HttpResponse(json.dumps(data), content_type='application/json')


def get_spsr_delivery_for_call_centr(request):
    city_name = request.POST.get('city_name')
    if city_name != 'Вся Россия':
        city = City.objects.filter(city_name=city_name).first()
        if not city:
            data = {'error': True,
                    'message': 'В ' + city_name + ' невозможно доставить заказ'
                    }
            return HttpResponse(json.dumps(data), content_type='application/json')

        to_city = str(city.city_id)
        products = request.POST.getlist('products[]')
        stocks = request.POST.getlist('stocks[]')
        lines = list(zip(products, stocks))
        lines_data = []
        spsr_info = {}
        price = 0
        for line in lines:
            current_prod = Product.objects.get(pk=int(line[0]))
            product_att = ProductAttributeValue.objects.filter(
                attribute__code__in=['weight', 'ind_weight'], product__id=line[0])
            weight = product_att.get(attribute__code='ind_weight').value_float or product_att.get(
                attribute__code='weight').value_float
            current_quantity = int(line[1])
            all_product_price_1 = current_prod.price_mrc * current_quantity
            price += all_product_price_1
            lines_data.append({'weight': weight,
                               'price_mrc': current_prod.price_mrc,
                               'quantity': current_quantity,
                               'product_id': current_prod.id})
        if str(city.city_id) == '49694102':
            lower_time_array = settings.ADDITIONAL_DAYS
            spsr_info['lptime'] = spsr_info['lptime_courier'] = spsr_info['lptime_pvz'] = get_date_format(lower_time_array, city.city_id)
            if int(price) >= settings.ORDER_SUM_FOR_FREE_SHIP:
                spsr_info['min_price'] = spsr_info['min_price_pvz'] = spsr_info['min_price_courier'] = 'Бесплатно'
            else:
                spsr_info['min_price'] = spsr_info['min_price_pvz'] = spsr_info['min_price_courier'] = '300'
            data = {
                'min_price': int(round(float(spsr_info['min_price']))),
                'lowest_time': spsr_info['lptime'],
                'min_price_courier': int(round(float(spsr_info['min_price_courier']))),
                'lowest_time_courier': spsr_info['lptime_courier'],
                'min_price_pvz': int(round(float(spsr_info['min_price_pvz']))),
                'lowest_time_pvz': spsr_info['lptime_pvz']
            }
        else:
            spsr_info = get_spsr_info(price, lines_data, city)
            data = {
                'min_price': int(round(float(spsr_info.get('min_price')))),
                'lowest_time': spsr_info.get('lptime'),
                'min_price_courier': int(round(float(spsr_info.get('min_price_courier')))),
                'lowest_time_courier': spsr_info.get('lptime_courier'),
                'min_price_pvz': int(round(float(spsr_info.get('min_price_pvz')))),
                'lowest_time_pvz': spsr_info.get('lptime_pvz')
            }

    return HttpResponse(json.dumps(data), content_type='application/json')


def check_stocks_for_basket(request):
    data = {}
    c = 0
    sub = request.POST.get('subscribe')
    if sub and sub != 'false':
        id_user = request.POST.get('id_user')
        user_info = User.objects.filter(id=id_user)
        if user_info:
            user_info.update(is_subscribed=1)
    for l in request.basket.lines.all():
        curr_product = l.product
        stock_reserve = StockReserve.objects.filter(line=l, is_active=True)
        if not stock_reserve:
            if curr_product.num_in_stock < curr_product.num_allocated + int(l.quantity):
                c += 1
                available = int(l.quantity) - curr_product.num_allocated
                if available == 0:
                    error_msg = str(c) + ". " + l.product.title + "- нет в наличии"
                else:
                    error_msg = str(c) + ". " + l.product.title + "- " + str(available) + "шт."

                data['error_' + str(l.product.pk)] = {
                    'stock': l.quantity,
                    'pk': l.product.pk,
                    'error': error_msg
                }

    return HttpResponse(json.dumps(data), content_type='application/json')


def register_customer_from_basket(request):
    post_data = request.POST.copy()
    post_data['email'] = post_data['email'].lower()
    if post_data['register'] == 'edit':
        phone = request.POST.get('phone')
        name = request.POST.get('last_name')
        print('last_name !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!==========', name)
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
        except:
            return HttpResponse(json.dumps({
                'errors_noreg': 'Неудалось найти пользователя с таким email'
            }),
                content_type='application/json')
        else:
            phone_user = PhoneUser.objects.filter(user=user).first()
            if phone_user:
                if phone_user.phone != phone:
                    phone_user.phone = phone
                    phone_user.save()
            else:
                phone_user = PhoneUser()
                phone_user.phone = phone
                phone_user.user = user
                phone_user.save()

            if user.last_name != name:
                user.last_name = name
                user.save()

            return HttpResponse(json.dumps({'user_id': user.id}), content_type='application/json')

    elif post_data['register'] == 'register':
        form_noreg = CustomCheckoutRegisterFormFromBasket(request, post_data)
        if form_noreg.is_valid():
            phone = request.POST.get('phone')
            password = User.objects.make_random_password(length=15)
            user = form_noreg.save(commit=False)
            user.set_password(password)
            user.save()
            if phone:
                phone_user = PhoneUser()
                phone_user.phone = phone
                phone_user.user = user
                phone_user.save()
            login(request, user)
            request.basket.owner = user
            ctx = dict()
            ctx['user'] = user
            ctx['password'] = password
            to = user.email
            subject, from_email = 'Вы зарегистрировались на Chadomarket.ru', 'no-reply@chadomarket.ru'
            html_content = get_template('mail/registration_mail.html').render(ctx)
            msg = EmailMultiAlternatives(subject, html_content, from_email, [to])
            msg.attach_alternative(html_content, "text/html")
            msg.send()
            # send_mail('Вы зарегистрировались на Chadomarket.ru', 'Логин:' + user.email + '  Пароль: ' + password + '',
            #           'no-reply@chadomarket.ru', ['' + user.email + ''])

            return HttpResponse(json.dumps({
                'token': csrf.get_token(request), 'user_id': user.id
            }), content_type='application/json')
        else:
            errors_noreg = form_noreg.errors
            return HttpResponse(json.dumps({
                'errors_noreg': errors_noreg
            }),
                content_type='application/json')
