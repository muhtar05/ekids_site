import datetime, json
from math import ceil
from django.conf import settings
from django.utils.timezone import utc
from itertools import chain
from django.db.models import Q, F
from rest_framework import serializers
from rest_framework.serializers import (
    ModelSerializer, ImageField,
    FileField, PrimaryKeyRelatedField,
)

from .models import Product, Category, ProductImage, Brand, ProductAttributeValue

from partner.models import StockRecord

from logistics_exchange.models import City
from common.context_processors import geo_city
from logistics_exchange.cart_tariff_calculate import Calc
from logistics_exchange.models import Office, OfficePickPoint
from common.views import month_to_year
from django.conf import settings


def get_date_format(lower_time_days, city_id):
    '''
    :param lower_time_array: количество дней доставки
    :param city_id: код города
    :return:
    '''
    # Функция позваляет перевести дату в селдующий вид '1 октября', '7 ноября'. Учитывает, что в выходные доставка
    # невозможна
    # - lower_time_array - кол-во дней доставки, которое возвращает система DPD
    #  - additional_days - добавочные дни, использовались для подстраховки, так как ТК не доставляла вовремя
    list_month = [
        u'января',
        u'февраля',
        u'марта',
        u'апреля',
        u'мая',
        u'июня',
        u'июля',
        u'августа',
        u'сентября',
        u'октября',
        u'ноября',
        u'декабря'
    ]
    time_now = datetime.datetime.now().strftime('%H')
    print('time_now === ', time_now)
    print('city_id === ', city_id)
    if str(city_id) == '49694102':
        print('time_now === ', time_now)
        if int(time_now) < 12:
            lptime = get_date_delivery(lower_time_days, 0, 'before_12', city_id)
        else:
            lptime = get_date_delivery(lower_time_days, 1, 'after_12', city_id)
    else:
        if int(time_now) < 12:
            lptime = get_date_delivery(lower_time_days, 0, 'before_12', city_id)
        else:
            lptime = get_date_delivery(lower_time_days, 1, 'before_12', city_id)

    lptime = lptime.strftime("%d ") + list_month[lptime.month - 1]

    return lptime


def get_date_delivery(days, additional_days, mode, city_id):
    """Получает дату доставки заказа по заданным параметрам"""
    print('days ==== ', days)
    now_date = datetime.date.today()
    # Если заказ совершен в субботу или воскресенье, то по Москве доставка во вторник,
    # по России начинаем отсчет от понедельника
    if now_date.weekday() == 6 or now_date.weekday() == 5:
        now_date = now_date + datetime.timedelta(7 - int(now_date.weekday()))
        if str(city_id) == '49694102':
            additional_days = 0
    # Прибавляем добавочные дни
    delta = datetime.timedelta(days=int(days) + additional_days)
    lptime = now_date + delta
    # Если доставка выпала на выходные переносим на понедельник, если заказ сделан до 12 часов и на вторник если после
    if lptime.weekday() == 6 or lptime.weekday() == 5:
        if mode == 'after_12' and now_date.weekday() == 4:
            delta_holiday = datetime.timedelta(8 - int(lptime.weekday()))
        else:
            delta_holiday = datetime.timedelta(7 - int(lptime.weekday()))
        lptime += delta_holiday

    return lptime


class CategorySerializer(ModelSerializer):
    class Meta:
        model = Category

        fields = (
            'id',
            'name',
        )


class ProductImageSerializer(ModelSerializer):
    class Meta:
        model = ProductImage
        fields = (
            'original',
            'display_order',
        )


class ProductStockSerializer(ModelSerializer):
    class Meta:
        model = StockRecord
        fields = (
            'num_in_stock',
            'num_allocated',
        )


class ProductSerializer(ModelSerializer):
    categories = CategorySerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    main_img = serializers.SerializerMethodField()
    price_mrc = serializers.SerializerMethodField()
    prod = serializers.SerializerMethodField()
    variants = serializers.SerializerMethodField()

    class Meta:
        model = Product

        fields = (
            'id',
            'title',
            'slug',
            'product_1c_id',
            'price_mrc',
            'categories',
            'images',
            'main_img',
            'prod',
            'variants',

        )

    def get_main_img(self, obj):
        img = obj.primary_image()
        return img

    def get_prod(self, obj):
        return obj

    def get_price_mrc(self, obj):
        price_mrc = int(obj.price_mrc)
        return price_mrc

    def get_variants(self, obj):
        return Product.objects.prefetch_related('images'). \
            filter(Q(item_id=obj.item_id),
                   Q(is_show=True),
                   Q(num_in_stock__gt=0),
                   Q(num_in_stock__gt=F('num_allocated'))). \
            exclude(item_id=None)

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.prefetch_related('categories', 'images', 'stockrecords')
        return queryset


class ProductDeliverySerialaizer(ModelSerializer):
    delivery = serializers.SerializerMethodField()

    class Meta:
        model = Product

        fields = (
            'delivery',
        )

    def get_delivery(self, obj):
        # получение сроков и стоимости доставки dpd по id продукта
        min_price = None
        min_price_courier = None
        lptime = None
        lptime_courier = None
        enable_apt = 0
        enable_pvz = 0
        city_object = geo_city(self.context['request'])['city_data']
        quantity = dict()

        if city_object:
            to_city_id = str(city_object.city_id)

            # Если Москва
            if to_city_id == '49694102':
                # В москве точно есть и ПВЗ и Постаматы, проверка не нужна
                enable_pvz = enable_apt = 1
                # Время доставки на следующий день по Москве (кроме выходных)
                lower_time_array = settings.ADDITIONAL_DAYS
                lptime_courier = lptime = get_date_format(lower_time_array, to_city_id)
                if int(obj.price_mrc) >= settings.ORDER_SUM_FOR_FREE_SHIP:
                    min_price = min_price_courier = 'Бесплатно'
                else:
                    min_price = min_price_courier = '300'
            # Если не Москва
            else:
                product_att = ProductAttributeValue.objects.filter(
                    attribute__code__in=['weight', 'ind_weight', 'ind_length', 'length', 'ind_width', 'width',
                                         'ind_height', 'height'], product=obj)
                # Проверяем на наличие ПВЗ и постаматы
                results = get_pvz_and_apt([obj], to_city_id)
                if results['offices_pvz'] or results['offices_pick_pvz']:
                    enable_pvz = 1
                else:
                    enable_pvz = 0
                if results['offices_pick_apt']:
                    enable_apt = 1
                else:
                    enable_apt = 0

                # Вычисляем курьерскую доставку
                delivery = Calc(city_object, [product_att], quantity, 'curier')
                # Вычисляем доставку в ПВЗ и постамат (стоимость доставки одинаковая)
                delivery_pvz = Calc(city_object, [product_att], quantity, 'pvz')

                # Форматируем стоимость и время доставки
                if delivery.min_price:
                    min_price_courier = ceil(float(delivery.min_price))
                else:
                    min_price_courier = None
                if delivery.lowest_price_time:
                    lptime_courier = get_date_format(delivery.lowest_price_time, to_city_id)
                else:
                    lptime_courier = None
                if delivery_pvz.min_price:
                    min_price = ceil(float(delivery_pvz.min_price))
                else:
                    min_price = None
                if delivery_pvz.lowest_price_time:
                    lptime = get_date_format(delivery_pvz.lowest_price_time, get_date_format)
                else:
                    lptime = None

        return {
            'min_price': min_price,
            'lowest_time': lptime,
            'min_price_courier': min_price_courier,
            'lowest_time_courier': lptime_courier,
            'enable_apt': enable_apt,
            'enable_pvz': enable_pvz
        }


class CityDeliverySerialaizer(ModelSerializer):
    delivery = serializers.SerializerMethodField()

    class Meta:
        model = City

        fields = (
            'delivery',
        )

    def get_delivery(self, obj):
        min_price = None
        min_price_courier = None
        lptime = None
        lptime_courier = None
        enable_apt = 0
        enable_pvz = 0
        city_object = obj
        quantity = dict()
        if city_object:
            city = obj
            product_att = {
                'weight': 1.0,
                'ind_weight': 1.0,
                'ind_length': 15.0,
                'length': 15.0,
                'ind_width': 15.0,
                'width': 15.0,
                'ind_height': 15.0,
                'height': 15.0
            }
            fix_size = OfficePickPoint.objects.filter(city_id=city.city_id)
            all_postamat = fix_size.filter(type_title='П')
            fix_size_pvz = fix_size.filter(type_title='ПВП')
            all_size = Office.objects.filter(city_id=city.city_id)
            all_pvz = chain(fix_size_pvz, all_size)
            # Создаем словарь для постаматов и пвз, чтобы взять только нужные данные и потом преобразовать в json
            postamat_dict = []
            pvz_dict = []
            for postamat in all_postamat:
                p = {
                    'unified_number': postamat.unified_number,
                    'street': postamat.street,
                    'street_abbr': postamat.street_abbr,
                    'house': postamat.house,
                    'building': postamat.building,
                    'delivery_shedule': postamat.delivery_schedule,
                    'latitude': postamat.latitude,
                    'longitude': postamat.longitude,
                    'type_title': postamat.type_title,
                    'descript': postamat.descript,
                }
                postamat_dict.append(p)
            for pvz in all_pvz:
                p = {
                    'unified_number': pvz.unified_number,
                    'street': pvz.street,
                    'street_abbr': pvz.street_abbr,
                    'house': pvz.house,
                    'building': pvz.building,
                    'delivery_shedule': pvz.delivery_schedule,
                    'latitude': pvz.latitude,
                    'longitude': pvz.longitude,
                }
                pvz_dict.append(p)

            if str(city.city_id) == '49694102':
                lower_time_array = 1
                lptime = lptime_courier = get_date_format(lower_time_array, city.city_id)
                min_price = min_price_courier = 'Бесплатно'

            else:
                delivery = Calc(city, [product_att], quantity, 'curier')
                delivery_pvz = Calc(city, [product_att], quantity, 'pvz')
                if delivery.min_price:
                    min_price_courier = ceil(float(delivery.min_price))
                else:
                    min_price_courier = None
                if delivery.lowest_price_time:
                    lptime_courier = get_date_format(delivery.lowest_price_time, city.city_id)
                else:
                    lptime_courier = None
                if delivery_pvz.min_price:
                    min_price = ceil(float(delivery_pvz.min_price))
                else:
                    min_price = None
                if delivery_pvz.lowest_price_time:
                    lptime = get_date_format(delivery_pvz.lowest_price_time, city.city_id)
                else:
                    lptime = None

        return {
            'min_price': min_price,
            'lowest_time': lptime,
            'min_price_courier': min_price_courier,
            'lowest_time_courier': lptime_courier,
            'enable_postomat': enable_apt,
            'enable_pvz': enable_pvz,
            'postomat': postamat_dict,
            'pvz': pvz_dict
        }


class ProductDetailSerializer(ModelSerializer):
    categories = CategorySerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    brand = serializers.SerializerMethodField()
    brand_option = serializers.SerializerMethodField()
    main_img = serializers.SerializerMethodField()
    price_mrc = serializers.SerializerMethodField()
    variants = serializers.SerializerMethodField()
    variant = serializers.SerializerMethodField()
    attributes = serializers.SerializerMethodField()
    attributes_order = serializers.SerializerMethodField()
    stockrecords = ProductStockSerializer(many=True, read_only=True)
    sizes_info = serializers.SerializerMethodField()
    all_sizes = serializers.SerializerMethodField()
    current_size = serializers.SerializerMethodField()
    price_with_discount = serializers.SerializerMethodField()
    discount_value = serializers.SerializerMethodField()

    class Meta:
        model = Product

        fields = (
            'id',
            'title',
            'slug',
            'product_1c_id',
            'artikul',
            'price_mrc',
            'categories',
            'images',
            'main_img',
            'brand',
            'brand_option',
            'rating',
            'variants',
            'variant',
            'attributes',
            'attributes_order',
            'all_sizes',
            'sizes_info',
            'current_size',
            'stockrecords',
            'item_id',
            'num_in_stock',
            'num_allocated',
            'price_with_discount',
            'is_discountable_status',
            'discount_value',
        )

    def get_main_img(self, obj):
        img = obj.primary_image()
        if isinstance(img, dict):
            return str(img['original'])
        return img.original.url

    def get_price_mrc(self, obj):
        price_mrc = int(obj.price_mrc)
        return price_mrc

    def get_brand_option(self, obj):
        product_brand = ProductAttributeValue.objects.filter(product=obj, attribute__code='brand').first()
        try:
            brand = product_brand.value_option.option
        except:
            brand = ''

        return brand

    def get_sizes_info(self, obj):
        data = {}
        if obj.size_item_id:
            size_items = Product.objects.values_list('size_item_id', flat=True).filter(item_id=obj.item_id).distinct()
            size_variants = Product.objects.filter(size_item_id__in=size_items)
            all_sizes = ProductAttributeValue.objects.filter(product_id__in=size_variants, attribute__code='size')\
                .values_list('value_option__show_value',flat=True).order_by('value_option__minimum').distinct()
            data['all_sizes'] = all_sizes
            size_products = Product.objects.filter(size_item_id=obj.size_item_id)
            size_color_variants = dict()
            for p in ProductAttributeValue.objects.filter(product__in=size_products, attribute__code='size'):
                size_color_variants[p.value_option.show_value] = {
                    'id': p.product.id,
                    'value': p.value_option.show_value,
                    'stock': p.product.get_stock_status(),
                }

            data['size_color_variants'] = size_color_variants
        return data

    def get_all_sizes(self, obj):
        data = []
        if obj.size_item_id:
            size_items = Product.objects.values_list('size_item_id', flat=True).filter(item_id=obj.item_id).distinct()
            size_variants = Product.objects.filter(size_item_id__in=size_items)
            size_products = Product.objects.filter(size_item_id=obj.size_item_id)
            current_sizes = [p.value_option.show_value for p in
                             ProductAttributeValue.objects.filter(product__in=size_products,
                                                                  attribute__code='size')]
            data = current_sizes
        return data

    def get_variants(self, obj):
        data = {}
        if (obj.item_id):
            variants = Product.objects.filter(Q(item_id=obj.item_id), Q(num_in_stock__gt=0),
                                              Q(num_in_stock__gt=F('num_allocated')))
            for variant in variants:
                img = variant.primary_image()
                if isinstance(img, dict):
                    original_img = str(img['original'])
                else:
                    original_img = img.original.url
                data[variant.pk] = [variant.pk, variant.title, original_img]
        return data

    def get_brand(self, obj):
        data = {}
        if obj.brand:
            data['name'] = obj.brand.name
            data['image'] = '/media/' + str(obj.brand.image) if obj.brand.image else None
            data['slug'] = obj.brand.slug
        else:
            product_brand = ProductAttributeValue.objects.filter(product=obj, attribute__code='brand').first()
            try:
                product_brand = product_brand.value_option.option
            except:
                data['name'] = None
                data['image'] = None
                data['slug'] = None
            else:
                brand = Brand.objects.filter(name=product_brand).first()
                if brand:
                    data['name'] = brand.name
                    data['image'] = '/media/' + str(brand.image) if brand.image else None
                    data['slug'] = brand.slug
                else:
                    data['name'] = None
                    data['image'] = None
                    data['slug'] = None
        return data

    def get_variant(self, obj):
        product_color = ProductAttributeValue.objects.filter(product=obj, attribute__code='color1').first()
        try:
            color = product_color.value_option.option
        except:
            color = ''

        return color

    def get_current_size(self, obj):
        return obj.get_size_value

    def get_attributes(self, obj):
        attributes_val = ProductAttributeValue.objects.filter(product=obj).order_by('attribute__display_order').exclude(attribute__type_group='transcharact')
        data = {}
        color, season = None, None
        for attribute_val in attributes_val:
            name = attribute_val.attribute.name
            att_type = attribute_val.attribute.type
            if str(att_type) == 'option':
                field = attribute_val.value_option.option
            elif str(att_type) == 'boolean':
                field = attribute_val.value_boolean
            elif str(att_type) == 'float':
                field = attribute_val.value_float
            elif str(att_type) == 'integer':
                field = attribute_val.value_integer
            elif str(att_type) == 'date':
                field = attribute_val.value_date
            else:
                field = attribute_val.value_text
            if attribute_val.attribute.code == 'age_from' or attribute_val.attribute.code == 'age_to':
                field = month_to_year(field)
            if attribute_val.attribute.code == 'color1' or attribute_val.attribute.code == 'color2' or attribute_val.attribute.code == 'color3':
                if color:
                    color += ', '+field
                else:
                    color = field
            elif attribute_val.attribute.code == 'season1' or attribute_val.attribute.code == 'season2' or attribute_val.attribute.code == 'season3':
                if season:
                    season += ', '+field
                else:
                    season = field
            else:
                data[name] = field
        if color:
            data['Цвет'] = color
        if season:
            data['Сезон'] = season
        return data

    def get_attributes_order(self, obj):
        attributes_val = ProductAttributeValue.objects.filter(product=obj).order_by('attribute__display_order').exclude(attribute__type_group='transcharact')
        data = []
        for attribute_val in attributes_val:
            if attribute_val.attribute.code == 'color1':
                name = 'Цвет'
                data.append(name)
            elif attribute_val.attribute.code == 'season1':
                name = 'Сезон'
                data.append(name)
            elif attribute_val.attribute.code == 'season2' or attribute_val.attribute.code == 'season3' or attribute_val.attribute.code == 'color2' or attribute_val.attribute.code == 'color3':
                continue
            else:
                name = attribute_val.attribute.name
                data.append(name)
        return data

    def get_price_with_discount(self, obj):
        return obj.get_discount_price()

    def get_is_discountable_status(self, obj):
        return obj.is_discountable_status()

    def get_discount_value(self, obj):
        discount = obj.get_discount()
        return discount.discount_value if discount else 0


def get_pvz_and_apt(basket_products, city_id):
    '''
    :param basket_products: товары для которые необходимо проверить по габаритам для ПВП и Постаматов (список)
    :param city_id: код города из системы DPD, для которого необходимо взять ПВП и Постаматы
    :return: Возвращает ПВП и Постаматы, в которые можно даставить данные товары

    Ф-ция берет ПВП и Постаматы определенного города, проверяет к каким товары похолдят по габаритам и возвращает
    список ПВП и Постаматов
    '''
    offices = Office.objects.filter(city_id=city_id)
    offices_dimensions_temp = offices_dimensions = OfficePickPoint.objects.filter(city_id=city_id)
    offices_bool = 1
    # Если нет ПВЗ и Постаматов то отдаем 0
    if not offices and not offices_dimensions:
        offices_bool = 0
    # Если есть ПВЗ и Постаматы - проверяем по габаритам товара только OfficePickPoint
    else:
        for product in basket_products:
            product_att = ProductAttributeValue.objects.filter(
                attribute__code__in=['ind_width', 'ind_height', 'ind_length', 'ind_weight', 'width', 'height',
                                     'length', 'weight'], product=product)

            # Берем длину ширину высоту и вес, если возвращается False переходим на следующую итерацию
            product_length = get_attribute_value(product_att, 'ind_length', 'length')
            if not product_length:
                offices_dimensions_temp = []
                continue
            product_width = get_attribute_value(product_att, 'ind_width', 'width')
            if not product_width:
                offices_dimensions_temp = []
                continue
            product_height = get_attribute_value(product_att, 'ind_height', 'height')
            if not product_height:
                offices_dimensions_temp = []
                continue
            product_weight = get_attribute_value(product_att, 'ind_weight', 'weight')
            if not product_weight:
                offices_dimensions_temp = []
                continue
            product_dimen = product_length + product_width + product_height

            for office in offices_dimensions_temp:
                if (office.max_height and office.max_length and office.max_width) and (office.max_weight or office.max_width or office.dimension_sum):
                    max_demensions = [float(office.max_length), float(office.max_height), float(office.max_width)]
                    product_dimensions = [float(product_length), float(product_height), float(product_width)]
                    max_demensions_sorted = sorted(max_demensions, reverse=True, key=float)
                    product_dimensions_sorted = sorted(product_dimensions, reverse=True, key=float)
                    if max_demensions_sorted and product_dimensions_sorted:
                        x1, y1, z1 = max_demensions_sorted[0], max_demensions_sorted[1], max_demensions_sorted[2]
                        x2, y2, z2 = product_dimensions_sorted[0], product_dimensions_sorted[1], product_dimensions_sorted[2]
                        if x2 > x1:
                            offices_dimensions_temp = offices_dimensions_temp.exclude(
                                unified_number=office.unified_number)
                            continue
                        if y2 > y1:
                            offices_dimensions_temp = offices_dimensions_temp.exclude(
                                unified_number=office.unified_number)
                            continue
                        if z2 > z1:
                            offices_dimensions_temp = offices_dimensions_temp.exclude(
                                unified_number=office.unified_number)
                            continue
                        if office.dimension_sum:
                            if float(product_dimen) > float(office.dimension_sum):
                                offices_dimensions_temp = offices_dimensions_temp.exclude(
                                    unified_number=office.unified_number)
                                continue
                        if office.max_weight:
                            if float(product_weight) > float(office.max_weight):
                                offices_dimensions_temp = offices_dimensions_temp.exclude(
                                    unified_number=office.unified_number)
                                continue
                    else:
                        offices_dimensions_temp = offices_dimensions_temp.exclude(
                            unified_number=office.unified_number)

    offices_check = 1
    if not offices and not offices_dimensions_temp:
        offices_check = 0

    offices_dimensions = offices_dimensions_temp
    offices_spsr_pvz = offices or None
    offices_pick_pvz = offices_dimensions.filter(type_title='ПВП') or None
    if offices_spsr_pvz and offices_pick_pvz:
        offices_uni = set(office.unified_number for office in offices_spsr_pvz)
        offices_dim_uni = set(office.unified_number for office in offices_pick_pvz)
        offices_dublicate = offices_uni & offices_dim_uni
        offices_spsr_pvz = offices_spsr_pvz.exclude(unified_number__in=offices_dublicate)

    offices_pick_post = offices_dimensions.filter(type_title='П') or None
    context = dict()
    context['offices_pvz'] = offices_spsr_pvz
    context['offices_pick_pvz'] = offices_pick_pvz
    context['offices_pick_apt'] = offices_pick_post
    context['offices_bool'] = offices_bool
    context['offices_check'] = offices_check
    return context


def get_subway(results_pvz_apt):
    subways = set()
    if 'offices_pvz' in results_pvz_apt and results_pvz_apt.get('offices_pvz'):
            for pvz in results_pvz_apt.get('offices_pvz'):
                if pvz.subway:
                    subways.add(pvz.subway)
    if 'offices_pick_pvz' in results_pvz_apt and results_pvz_apt.get('offices_pick_pvz'):
            for pvz in results_pvz_apt.get('offices_pick_pvz'):
                if pvz.subway:
                    subways.add(pvz.subway)
    if 'offices_pick_apt' in results_pvz_apt and results_pvz_apt.get('offices_pick_apt'):
            for pvz in results_pvz_apt.get('offices_pick_apt'):
                if pvz.subway:
                    subways.add(pvz.subway)
    return sorted(list(subways))


def get_attribute_value(product_atts, transp_att_name, main_att_name):
    '''
    :param product_atts: Queryset содержащий все значения аттрибуто взяты у товара (длина, ширина, высота и тд)
    :param transp_att_name: Код аттрибута, который нужно взять (транспортный аттр.)
    :param main_att_name: Код аттрибута, который нужно взять (основной аттр.)
    :return: product_dimension: Значение запрашиваемой величины (аттрибута)

    Ф-ция фильтрует изначально по транспортному значению, если ничего не возвращается, то фильтрует по основному,
    если снова ничего не возвращается, то вовращается False - товар не войдет ни в один ПВП.
    '''

    product_dimension = product_atts.filter(attribute__code=transp_att_name).first()
    if not product_dimension:
        product_dimension = product_atts.filter(attribute__code=main_att_name).first()
        if product_dimension:
            product_dimension = product_dimension.value_float
        else:
            product_dimension = False
    else:
        product_dimension = product_dimension.value_float

    return product_dimension
