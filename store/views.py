import datetime
from random import randint
from django.utils import timezone
from django.shortcuts import render
from django.http import HttpResponse

from catalogue.models import Product, Brand, ProductAttributeValue
from django.db.models import Q, F, Count
from discountmanager.models import Discount


def get_random_index():
    now_date = timezone.now()
    sales_products = Product.objects.filter(Q(discounts__isnull=False), Q(discounts__start_datetime__lte=now_date),
                                            Q(num_in_stock__gt=0), Q(num_in_stock__gt=F('num_allocated')),
                                            Q(discounts__end_datetime__gte=now_date))
    count = sales_products.aggregate(count=Count('id'))['count']
    random_index = randint(0, count - 1) if count else 0
    return random_index


def home(request):
    today = datetime.date.today()
    ten_days_ago = today - datetime.timedelta(days=10)
    offset_index = get_random_index()
    limit_index = offset_index + 10
    now_date = timezone.now()
    sales_products = Product.objects.filter(Q(discounts__isnull=False), Q(discounts__start_datetime__lte=now_date),
                                            Q(discounts__end_datetime__gte=now_date), Q(num_in_stock__gt=0),
                                            Q(num_in_stock__gt=F('num_allocated')))[offset_index:limit_index]

    first_product_queryset = Product.objects.filter(Q(price_mrc__gt=0),Q(is_show=True),
                                           Q(date_created__date__range=[ten_days_ago,today]),
                                           Q(num_in_stock__gt=0),Q(num_in_stock__gt=F('num_allocated'))).\
                                           order_by('-date_created')

    first_product = first_product_queryset[:10]

    # Получаем все бренды из модели Brand
    brands = Brand.objects.filter(image__isnull=False).order_by('display_order')[:16]

    now_date = timezone.now()
    current_discounts_with_banners = Discount.objects.filter(is_show_banner=True, start_datetime__lte=now_date,
                                                             end_datetime__gte=now_date). \
        exclude(Q(banner__isnull=True) | Q(banner=''))

    ctx = {}
    # ctx['first_product_variants'] = first_product_variants
    ctx['first_product'] = first_product
    ctx['banners'] = current_discounts_with_banners
    ctx['brands'] = brands
    ctx['sales_products'] = sales_products
    response = render(request, 'home.html', ctx)
    response.set_cookie('current_prev', request.path)
    return response


def home_test(request):
    today = datetime.date.today()
    ten_days_ago = today - datetime.timedelta(days=30)
    offset_index = get_random_index()
    limit_index = offset_index +  10
    sales_products = Product.objects.filter(discounts__isnull=False)[offset_index:limit_index]
    first_product = Product.objects.filter(Q(price_mrc__gt=0),Q(is_show=True),
                                            Q(date_created__range=[ten_days_ago,today]),
                                            Q(num_in_stock__gt=0),Q(num_in_stock__gt=F('num_allocated'))).\
                                distinct()[:10]

    item_ids = [p.item_id for p in first_product]

    brand_ids = Product.objects.values_list('brand', flat=True).filter(num_in_stock__gt=0).distinct()
    brands = Brand.objects.filter(id__in=brand_ids).order_by('display_order')
    now_date = timezone.now()
    current_discounts_with_banners = Discount.objects.filter(start_datetime__lte=now_date, end_datetime__gte=now_date). \
        exclude(Q(banner__isnull=True) | Q(banner=''))

    ctx = {}
    # ctx['first_product_variants'] = first_product_variants
    ctx['first_product'] = first_product
    ctx['banners'] = current_discounts_with_banners
    ctx['brands'] = brands[:16]
    ctx['sales_products'] = sales_products
    response = render(request, 'home_test.html', ctx)
    response.set_cookie('current_prev', request.path)
    return response


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[-1].strip()
    elif request.META.get('HTTP_X_REAL_IP'):
        ip = request.META.get('HTTP_X_REAL_IP')
    else:
        ip = request.META.get('REMOTE_ADDR')
    return HttpResponse(ip)
