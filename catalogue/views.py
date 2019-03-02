import datetime, warnings, re, json, os
from collections import OrderedDict, namedtuple
from itertools import chain
from htmlmin.minify import html_minify

from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.db import connection
from django.core.paginator import (Paginator, EmptyPage,
                                   PageNotAnInteger,
                                   )
from django.http import (Http404, HttpResponsePermanentRedirect,
                         HttpResponse,
                         )
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.views.generic import DetailView, TemplateView, View
from django.db.models import Q, F, Max, Min, Count, Case, When, IntegerField
from django.utils import timezone

from common.context_processors import geo_city
from common.forms import FeedbackForm
from logistics_exchange.models import City
from catalogue.signals import product_viewed
from catalogue.reviews.forms import ProductReviewForm, ReviewCommentForm
from basket.views import get_date_format
from seo.models import SeoModuleProducts, SeoModule, SeoModuleFilterUrls
from discountmanager.models import Discount
from .models import (Product, Category,
                     FilterItem, Brand, ProductAttributeValue,
                     ProductAttribute, ProductAttributeOption,
                     )


class CommonFilterGetDataMixin(object):
    def get_filter_result(self, filter_options):
        filter_result = OrderedDict()
        for f_opt in filter_options:
            current_ids = filter_result.get(f_opt[0], set())
            current_ids.add(f_opt[1])
            filter_result[f_opt[0]] = current_ids

        for key, val in filter_result.items():
            filter_result[key] = list(val)
        return filter_result

    def get_filter_float_result(self, filter_options):
        filter_result = OrderedDict()
        for f_opt in filter_options:
            current_ids = filter_result.get(f_opt[0], set())
            current_ids.add(f_opt[1])
            filter_result[f_opt[0]] = current_ids

        for key, val in filter_result.items():
            val = list(val)
            max_value = max(val)
            min_value = min(val)
            filter_result[key] = [min_value, max_value]
        return filter_result


class ProductView(View):
    def get(self, request, *args, **kwargs):
        # self.object = product = Product.objects.get()
        pass


class SeoModuleCatalogueBrand(object):
    all_varieties = dict()

    def get_meta_tags(self, model, model_url, item, min_price, count):
        rules_dict = dict()
        ctx = {}
        main_rule = None
        if model == 'Seo':
            main_rule = model_url
        else:
            rules = SeoModule.objects.filter(model_name=model).order_by('priority')
            current_url = '/' + str(model_url) + '/' + str(item['slug'] + '/')
            for rule in rules:
                rule_url = rule.template_url
                if len(re.findall(r'' + str(rule_url) + '', current_url)) > 0:
                    main_rule = rule
                    break
        if main_rule:
            rules_dict['seo_h1'] = []
            rules_dict['seo_h1'].append(re.findall(r'{.*?}', main_rule.h1))
            rules_dict['seo_h1'].append(main_rule.h1)
            rules_dict['seo_title'] = []
            rules_dict['seo_title'].append(re.findall(r'{.*?}', main_rule.title))
            rules_dict['seo_title'].append(main_rule.title)
            rules_dict['seo_description'] = []
            rules_dict['seo_description'].append(re.findall(r'{.*?}', main_rule.description))
            rules_dict['seo_description'].append(main_rule.description)
            rules_dict['seo_keywords'] = []
            rules_dict['seo_keywords'].append(re.findall(r'{.*?}', main_rule.keywords))
            rules_dict['seo_keywords'].append(main_rule.keywords)
            rules_dict['seo_text'] = []
            rules_dict['seo_text'].append(re.findall(r'{.*?}', main_rule.seo_text))
            rules_dict['seo_text'].append(main_rule.seo_text)
            self.all_varieties = {}
            for key, rule_one in rules_dict.items():
                ctx[key] = self.get_variety(rule_one[0], item, rule_one[1], model, min_price, count)
        else:
            ctx['seo_h1'] = ''
            ctx['seo_title'] = ''
            ctx['seo_description'] = ''
            ctx['seo_keywords'] = ''
            ctx['seo_text'] = ''

        return ctx

    def get_variety(self, variety, item, rule, model, min_price=0, count=0):
        for var in variety:
            if model != 'Brand' and rule.find(str(var)) == 0:
                upper = True
            else:
                upper = False
            var_strip = var.replace('{', '').replace('}', '').strip()
            if var_strip in item:
                if type(item[var_strip]) is not str:
                    try:
                        product_var = int(item[var_strip])
                    except:
                        product_var = item[var_strip]
                else:
                    product_var = item[var_strip]
                if upper:
                    rule = rule.replace(var, str(product_var).capitalize(), 1)
                    rule = rule.replace(var, str(product_var))
                else:
                    rule = rule.replace(var, str(product_var))
            else:
                if var_strip in self.all_varieties:
                    if upper:
                        rule = rule.replace(var, str(self.all_varieties[str(var_strip)]).capitalize(), 1)
                        rule = rule.replace(var, str(self.all_varieties[str(var_strip)]))
                    else:
                        rule = rule.replace(var, str(self.all_varieties[str(var_strip)]))
                else:
                    if var_strip.find('|') == -1:
                        if var_strip == "min_price":
                            try:
                                min_price = str(int(min_price))
                            except:
                                min_price = str(min_price)
                            rule = rule.replace(var, min_price)
                        elif var_strip == "count":
                            rule = rule.replace(var, str(count))
                            self.all_varieties[str(var_strip)] = str(count)
                    else:
                        var_and_model = var_strip.split('|')
                        model = var_and_model[0]
                        if model == 'Location':
                            field = str(var_and_model[1])
                            product_var = City.objects.filter(city_id='49694102').values(field)[0]
                            rule = rule.replace(var, str(product_var[field]))
                            if upper:
                                rule = rule.replace(var, str(product_var[field]).capitalize(), 1)
                                rule = rule.replace(var, str(product_var[field]))
                            else:
                                rule = rule.replace(var, str(product_var))
                            self.all_varieties[str(var_strip)] = product_var[field]
        return rule


class ProductDetailView(DetailView):
    model = Product
    template_name = 'catalogue/product.html'
    context_object_name = 'product'
    view_signal = product_viewed
    form_review = ProductReviewForm
    form_comment = ReviewCommentForm
    form_feedback = FeedbackForm
    all_varieties = dict()

    def get(self, request, **kwargs):
        try:
            self.temp_product = product_temp = Product.objects. \
                filter(slug=kwargs.get('product_slug'), pk=kwargs.get('pk')). \
                prefetch_related('images')
            # Если товар не найден, проверяем возможно перешли по старому url товара
            # Если так, то нужно сделать редирект на новый url товара
            if not self.temp_product:
                product_temp = Product.objects. \
                    filter(old_slug=kwargs.get('product_slug'), pk=kwargs.get('pk')). \
                    prefetch_related('images')
                if product_temp:
                    product_temp = product_temp.first()
                    print('product_temp === ', product_temp)
                    return HttpResponsePermanentRedirect(
                        '/product/' + str(product_temp.slug) + '_' + str(product_temp.pk) + '/')

            self.object = product = product_temp.first()
        except:
            raise Http404()

        if self.object is None or not self.object:
            raise Http404()

        response = super().get(request, **kwargs)
        self.send_signal(request, response, product)
        return response

    def get_object(self, queryset=None):
        # Check if self.object is already set to prevent unnecessary DB calls
        if hasattr(self, 'object'):
            return self.object
        else:
            return super().get_object(queryset)

    def get_meta_tags(self, product):
        rule = SeoModuleProducts.objects.first()
        rules_dict = dict()
        ctx = {}
        if rule:
            rules_dict['seo_h1'] = []
            rules_dict['seo_h1'].append(re.findall(r'{.*?}', rule.h1))
            rules_dict['seo_h1'].append(rule.h1)
            rules_dict['seo_title'] = []
            rules_dict['seo_title'].append(re.findall(r'{.*?}', rule.title))
            rules_dict['seo_title'].append(rule.title)
            rules_dict['seo_description'] = []
            rules_dict['seo_description'].append(re.findall(r'{.*?}', rule.description))
            rules_dict['seo_description'].append(rule.description)
            rules_dict['seo_keywords'] = []
            rules_dict['seo_keywords'].append(re.findall(r'{.*?}', rule.keywords))
            rules_dict['seo_keywords'].append(rule.keywords)
            rules_dict['seo_text'] = []
            rules_dict['seo_text'].append(re.findall(r'{.*?}', rule.seo_text))
            rules_dict['seo_text'].append(rule.seo_text)
            for key, rule_one in rules_dict.items():
                ctx[key] = self.get_variety(rule_one[0], product, rule_one[1])
        else:
            ctx['seo_h1'] = ''
            ctx['seo_title'] = ''
            ctx['seo_description'] = ''
            ctx['seo_keywords'] = ''
            ctx['seo_text'] = ''

        return ctx

    def get_variety(self, variety, product, rule):
        for var in variety:
            var_strip = var.replace('{', '').replace('}', '').strip()
            if var_strip in product:
                if type(product[var_strip]) is not str:
                    try:
                        product_var = int(product[var_strip])
                    except:
                        product_var = product[var_strip]
                else:
                    product_var = product[var_strip]
                rule = rule.replace(var, str(product_var))
            else:
                if var_strip in self.all_varieties:
                    rule = rule.replace(var, str(self.all_varieties[str(var_strip)]))
                else:
                    var_and_model = var_strip.split('|')
                    model = var_and_model[0]
                    if model == 'Location':
                        field = str(var_and_model[1])
                        product_var = City.objects.filter(city_id='49694102').values(field)[0]
                        rule = rule.replace(var, str(product_var[field]))
                        self.all_varieties[str(var_strip)] = product_var[field]
        return rule

    def get_context_data(self, **kwargs):
        meta_tags = self.get_meta_tags(self.temp_product.values()[0])
        ctx = super().get_context_data(**kwargs)
        if geo_city(self.request)['city_data']:
            city = geo_city(self.request)['city_data']
            ctx['city_id'] = city.city_id
        else:
            city_name = 'Вся Россия'
            ctx['city_name'] = city_name
        lower_time_array = settings.ADDITIONAL_DAYS
        day_for_free_delivery = get_date_format(lower_time_array, city.city_id)

        variants = Product.objects.values('pk', 'main_image', 'size_item_id'). \
            filter(Q(item_id=self.object.item_id),
                   Q(is_show=True),
                   Q(num_in_stock__gt=0),
                   Q(num_in_stock__gt=F('num_allocated'))). \
            exclude(pk=self.object.pk)

        if self.object.size_item_id:
            size_items = Product.objects.values_list('size_item_id', flat=True).filter(
                item_id=self.object.item_id).distinct()
            size_variants = Product.objects.filter(size_item_id__in=size_items)
            ctx['size_variants'] = size_variants
            all_sizes = ProductAttributeValue.objects.filter(product_id__in=size_variants, attribute__code='size') \
                .values_list('value_option__show_value', flat=True).order_by('value_option__minimum').distinct()
            ctx['all_sizes'] = all_sizes
            size_products = Product.objects.filter(size_item_id=self.object.size_item_id)
            ctx['size_color_variants'] = [p.value_option.show_value for p in
                                          ProductAttributeValue.objects.filter(product__in=size_products,
                                                                               attribute__code='size')]
            size_color_variants_stock = [p.value_option.show_value for p in
                                         ProductAttributeValue.objects.filter(product__in=size_products,
                                                                              attribute__code='size') if
                                         p.product.get_stock_status()]

            ctx['size_color_variants_stock'] = size_color_variants_stock

        brand_info = self.object.get_brand_info()

        ctx['brand_info'] = brand_info
        ctx['meta_tags'] = meta_tags
        ctx['form_review'] = self.form_review(product=self.object, user=self.request.user)
        ctx['form_comment'] = self.form_comment()
        ctx['form_feedback'] = self.form_feedback()
        ctx['variants'] = variants
        ctx['main_image'] = self.object.main_image
        ctx['day_for_free_delivery'] = day_for_free_delivery

        return ctx

    def send_signal(self, request, response, product):
        self.view_signal.send(
            sender=self, product=product, user=request.user, request=request,
            response=response)


class BrandList(TemplateView):
    template_name = 'catalogue/brand_list.html'

    def get(self, request, *args, **kwargs):
        self.brands = Brand.objects.all().order_by('name')
        letters_array = []
        brands_array = dict()

        for brand in self.brands:
            first_letter = str(brand.name)[0].upper()
            if first_letter not in letters_array:
                letters_array.append(first_letter)
                brands_array[first_letter] = []
            brands_array[first_letter].append(brand)

        letters_array.sort()

        return render(request, self.template_name, {
            'brands': brands_array, 'letters': letters_array
        })


class BrandPage(SeoModuleCatalogueBrand, CommonFilterGetDataMixin, View):
    def __init__(self):
        self.template_name = 'catalogue/brand_self.html'

    def get_all_variants(self, item_ids):
        all_variants = Product.objects.values('pk', 'item_id', 'title', 'main_image'). \
            filter(Q(item_id__in=item_ids),
                   Q(is_show=True),
                   Q(num_in_stock__gt=0),
                   Q(num_in_stock__gt=F('num_allocated'))). \
            exclude(item_id=None)
        return all_variants

    def get(self, request, *args, **kwargs):
        slug = kwargs.get('slug')
        brand = Brand.objects.filter(slug=slug).first()
        if not brand:
            raise Http404('')

        option_id = ProductAttributeOption.objects.filter(id=brand.id_option).first()
        all_product_ids = set(ProductAttributeValue.objects.values_list('product_id', flat=True). \
                              filter(attribute__code='brand',
                                     product__is_show=True,
                                     value_option_id=option_id.id))

        product_stock = Product.objects.filter(Q(id__in=all_product_ids),
                                               Q(is_show=True),
                                               Q(num_in_stock__gt=0),
                                               Q(num_in_stock__gt=F('num_allocated'))). \
            order_by('-date_created')

        product_unstock = Product.objects.filter(Q(id__in=all_product_ids),
                                                 Q(is_show=True),
                                                 (Q(num_in_stock=F('num_allocated')) |
                                                  Q(num_in_stock=0))).order_by('-date_created')

        categories_ids = Product.objects.values_list('categories__id', flat=True). \
            filter(id__in=all_product_ids).distinct()

        categories_list = Category.objects.filter(id__in=categories_ids)
        results = list(chain(product_stock, product_unstock))
        count_products = len(results)
        if results:
            pages = Paginator(results, 30)
            try:
                pages_content = pages.page(1)
            except PageNotAnInteger:
                pages_content = pages.page(1)
            except EmptyPage:
                pages_content = pages.page(pages.num_pages)
        else:
            pages_content = ''
            pages = ''

        max_price_stock = product_stock.aggregate(Max('price_mrc')).get('price_mrc__max') or 0
        max_price_unstock = product_unstock.aggregate(Max('price_mrc')).get('price_mrc__max') or 0
        min_price_seo = product_stock.aggregate(Min('price_mrc'))['price_mrc__min'] or 0
        brand_dict = Brand.objects.filter(slug=slug).values()[0]

        meta_tags = self.get_meta_tags('Brand', 'brand', brand_dict, min_price_seo, count_products)

        min_price = 0
        max_price = max_price_stock if max_price_stock > max_price_unstock else max_price_unstock
        stock_yes, unstock_yes = False, False
        discount_value = None
        discount_ids = []
        if pages_content:
            for p in pages_content:
                current_num = p.num_in_stock
                if current_num > 0:
                    stock_yes = True
                if current_num == 0:
                    unstock_yes = True
                    # Код который может понадобиться при оптимизации
                    # now_today = timezone.now()
                    # active_discount = Discount.objects.filter(start_datetime__lte=now_today, end_datetime__gte=now_today).first()
                    # if active_discount:
                    #     print("active discount")
                    #     discount_value = active_discount.discount_value
                    #     temp_product_ids = [p.id for p in pages_content]
                    #     print("temp_pr", temp_product_ids)
                    #     discount_ids = list(active_discount.products.filter(id__in=temp_product_ids).values_list('id', flat=True))

        product_ids = set(ProductAttributeValue.objects.values_list('product_id', flat=True). \
                          filter(attribute__code='brand',
                                 value_option_id=option_id.id,
                                 product__price_mrc__gte=min_price,
                                 product__price_mrc__lte=max_price
                                 ))

        filter_options = ProductAttributeValue.objects.values_list('attribute_id', 'value_option_id'). \
            filter(Q(product_id__in=product_ids),
                   Q(attribute__is_show=True)).order_by('attribute__display_order')

        filter_result = self.get_filter_result(filter_options)

        main_attributes = ProductAttribute.objects.filter(is_main=True)
        item_ids = [p.item_id for p in pages_content]
        all_variants = self.get_all_variants(item_ids)
        print("Max_price", max_price)

        # filter_value_range = ProductAttributeValue.objects.values('attribute_id'). \
        #     annotate(min_value=Min('value_float'), max_value=Max('value_float')). \
        #     filter(Q(value_float__isnull=False),
        #            Q(product__price_mrc__gte=min_price),
        #            Q(product__price_mrc__lte=max_price),
        #            Q(product__categories__in=categories_ids),
        #            Q(attribute__is_show=True)).order_by('attribute__display_order')

        print("End brand get {}".format(slug))
        print(discount_ids)
        print(discount_value)
        response = render(request, self.template_name, {
            'brand': brand,
            'meta_tags': meta_tags,
            'results': pages_content,
            'pages': pages,
            'categories': categories_list,
            'categories_ids': categories_ids,
            'stock_yes': stock_yes,
            'unstock_yes': unstock_yes,
            'min_price_slider': min_price,
            'max_price_slider': max_price,
            'min_price': min_price,
            'max_price': max_price,
            'count_products': count_products,
            'filter_options': filter_options,
            'main_attributes': main_attributes,
            'filter_result': filter_result,
            'all_variants': all_variants,
            'discount_value': discount_value,
            'discount_ids': discount_ids,
        })
        response.set_cookie('current_prev', request.path)
        return response


def get_filter_data(request):
    categories_ids = request.GET.getlist('categories[]')

    products_list = Product.objects.filter(categories__in=categories_ids, price_mrc__gt=0).prefetch_related(
        'images')

    min_price = products_list.aggregate(Min('price_mrc'))['price_mrc__min'] or 0
    max_price = products_list.aggregate(Max('price_mrc'))['price_mrc__max'] or 0

    filter_fields = FilterItem.objects.filter(show=True)
    filters_fields_result = OrderedDict()
    for field in filter_fields:
        if not 'brand' in field.code:
            unique_values = list(set([getattr(p, field.code) for p in products_list
                                      if getattr(p, field.code)]))

            if 'sex' in field.code:
                filters_fields_result[field.name] = [{Product.STATUS_CHOICES[uv][1]: uv} for uv in unique_values]
            else:
                filters_fields_result[field.name] = [{uv: uv} for uv in unique_values]

    data = {'status': 'ok',
            'min_price': float(min_price),
            'max_price': float(max_price),
            'filter_fields': filters_fields_result,
            }

    return HttpResponse(json.dumps(data), content_type='application/json')


class BrandsSitemap(Sitemap):
    priority = 0.9

    def items(self):
        return Brand.objects.all()


class CategoriesSitemap(Sitemap):
    priority = 0.9

    def items(self):
        return Category.objects.exclude(name='_root').order_by('lft')


class ProductsSitemap(Sitemap):
    priority = 0.8

    def items(self):
        return Product.objects.filter(Q(price_mrc__gt=0),
                                      Q(num_in_stock__gt=0),
                                      Q(num_in_stock__gt=F('num_allocated'))).distinct()


class SeoFilterSitemap(Sitemap):
    priority = 0.9

    def items(self):
        return SeoModuleFilterUrls.objects.filter(has_product=True)


class CommonSqlMixin(object):
    def get_sql_fields(self):
        sql_fields = '''"catalogue_product"."id", "catalogue_product"."title",
                      "catalogue_product"."slug","catalogue_product"."price_mrc",
                      "catalogue_product"."date_created","catalogue_product"."rating",
                      "catalogue_productimage"."original", "catalogue_productimage"."display_order",
                      "catalogue_product"."item_id","partner_stockrecord"."num_in_stock",
                      "partner_stockrecord"."num_allocated","partner_stockrecord"."price_excl_tax"
        '''
        return sql_fields

    def get_common_left_joines(self):
        common_left_joines = '''LEFT OUTER JOIN "catalogue_productimage" ON ("catalogue_product"."id" = "catalogue_productimage"."product_id")
                                LEFT OUTER JOIN "partner_stockrecord" ON ("catalogue_product"."id" = "partner_stockrecord"."product_id")
                                LEFT OUTER JOIN "catalogue_productcategory" ON ("catalogue_product"."id" = "catalogue_productcategory"."product_id")
                                LEFT OUTER JOIN "catalogue_category" ON ("catalogue_productcategory"."category_id" = "catalogue_category"."id")
        '''
        return common_left_joines


class ProductCategoryView(SeoModuleCatalogueBrand, View):
    """
    Browse products in a given category
    """
    context_object_name = "products"
    template_name = 'catalogue/category.html'
    template_parent_name = 'catalogue/parent_category.html'
    enforce_paths = True

    def get_filter_result(self, filter_options):
        filter_result = OrderedDict()
        for f_opt in filter_options:
            current_ids = filter_result.get(f_opt[0], set())
            current_ids.add(f_opt[1])
            filter_result[f_opt[0]] = current_ids

        for key, val in filter_result.items():
            filter_result[key] = list(val)
        return filter_result

    def get_filter_float_result(self, filter_options):
        filter_result = OrderedDict()
        for f_opt in filter_options:
            current_ids = filter_result.get(f_opt[0], set())
            current_ids.add(f_opt[1])
            filter_result[f_opt[0]] = current_ids

        for key, val in filter_result.items():
            val = list(val)
            max_value = max(val)
            min_value = min(val)
            filter_result[key] = [min_value, max_value]
        return filter_result

    def get_sql_fields(self):
        sql_fields = '''"catalogue_product"."id", "catalogue_product"."title",
                      "catalogue_product"."slug","catalogue_product"."price_mrc",
                      "catalogue_product"."date_created","catalogue_product"."rating",
                      "catalogue_productimage"."original", "catalogue_productimage"."display_order",
                      "catalogue_product"."item_id","catalogue_product"."num_in_stock",
                      "catalogue_product"."num_allocated"
        '''
        return sql_fields

    def get_common_left_joines(self):
        common_left_joines = '''LEFT OUTER JOIN "catalogue_productimage" ON ("catalogue_product"."id" = "catalogue_productimage"."product_id")
                            LEFT OUTER JOIN "catalogue_productcategory" ON ("catalogue_product"."id" = "catalogue_productcategory"."product_id")
                            LEFT OUTER JOIN "catalogue_category" ON ("catalogue_productcategory"."category_id" = "catalogue_category"."id")
        '''
        return common_left_joines

    def get_price_value(self, sql, cursor):
        cursor.execute(sql)
        data_info = cursor.fetchone()
        price = int(data_info[0]) if data_info[0] else 0
        return price

    def get_all_variants(self, item_ids):
        return Product.objects.values('pk', 'item_id', 'title', 'main_image'). \
            filter(Q(item_id__in=item_ids),
                   Q(is_show=True),
                   Q(num_in_stock__gt=0),
                   Q(num_in_stock__gt=F('num_allocated'))). \
            exclude(item_id=None)

    def get_brands(self, products_list):
        ids = [p.pk for p in products_list]
        brand_oprion_ids = ProductAttributeValue.objects.values_list('value_option_id', flat=True). \
            filter(attribute__code='brand', product__is_show=True, product__id__in=ids).distinct()

        brands_list_result = Brand.objects.filter(id_option__in=brand_oprion_ids).order_by('name')
        return brands_list_result

    def get_ordering_condition(self, param):
        if '-price' == param:
            condition = '-price_mrc'
        elif 'price' == param:
            condition = 'price_mrc'
        elif '-new' == param:
            condition = '-date_created'
        elif 'new' == param:
            condition = 'date_created'
        elif 'rating' == param:
            condition = 'rating'
        elif '-rating' == param:
            condition = '-rating'
        elif 'reviews' == param:
            condition = 'num_reviews'
        elif '-reviews' == param:
            condition = '-num_reviews'
        else:
            condition = 'price_mrc'
        return condition

    def get_category(self):
        if 'category_slug' in self.kwargs:
            return get_object_or_404(Category, category_slug=self.kwargs['category_slug'])
        elif 'category_slug' in self.kwargs:
            concatenated_slugs = self.kwargs['category_slug']
            slugs = concatenated_slugs.split(Category._slug_separator)
            try:
                last_slug = slugs[-1]
            except IndexError:
                raise Http404
            else:
                for category in Category.objects.filter(slug=last_slug):
                    if category.full_slug == concatenated_slugs:
                        message = (
                            "Accessing categories without a primary key"
                            " is deprecated will be removed in Oscar 1.2.")
                        warnings.warn(message, DeprecationWarning)

                        return category

        raise Http404

    def get_categories(self):
        return self.category.get_descendants_and_self()

    def get_stock_info(self, products):
        stock_yes, unstock_yes = False, False
        for p in products:
            current_num = p.get('num_in_stock')
            if current_num > 0:
                stock_yes = True
            if current_num == 0:
                unstock_yes = True
                break

        return {
            'stock_yes': stock_yes,
            'unstock_yes': unstock_yes,
        }

    def get_stock_info_seo(self, products):
        stock_yes, unstock_yes = False, False
        stock_count = 0
        for p in products:
            current_num = p.num_in_stock
            if current_num > 0:
                stock_count += 1
                stock_yes = True
            if current_num == 0:
                unstock_yes = True
                break

        return {
            'stock_yes': stock_yes,
            'unstock_yes': unstock_yes,
            'stock_count': stock_count,
        }

    def get_parent_category_name(self, category):
        if category.level > 2:
            parent_category = category.get_ancestors().filter(level=2).first()
            return parent_category.name
        else:
            return category.name

    def get(self, request, *args, **kwargs):
        print(str(datetime.datetime.now()))
        begin = datetime.datetime.now()

        url_seo = None
        category_temp = Category.objects.prefetch_related('children', 'parent').filter(slug=kwargs.get('category_slug'))
        self.category = category_temp.first()
        if category_temp:
            categories_for_seo = category_temp.values()[0]

        if not category_temp:
            url_seo = SeoModuleFilterUrls.objects.filter(url=kwargs.get('category_slug'), has_product=True).first()
            if not url_seo:
                raise Http404()
        if url_seo:
            try:
                description_array = json.loads(url_seo.description_array)
                category_temp = Category.objects.prefetch_related('children', 'parent'). \
                    filter(id=int(description_array['category']))
                categories_for_seo = category_temp.values()[0]
                self.category = category_temp.first()
            except Exception as e:
                print(str(e))
                raise Http404()
        try:
            categories = self.category.get_children()
        except:
            raise Http404()

        if self.category.parent.name == '_root' and not url_seo:
            page_type = 'Список категорий товаров'
            categories_ids = categories.get_descendants().values_list('id', flat=True)

            all_products_list = Product.objects.filter(Q(categories__in=categories_ids))
            count_products = all_products_list.count()

            products_list = all_products_list.filter(Q(price_mrc__gt=0),
                                                     Q(is_show=True),
                                                     Q(num_in_stock__gt=0),
                                                     Q(num_in_stock__gt=F('num_allocated')))
            brands = self.get_brands(products_list)
            min_price_seo = products_list.aggregate(Min('price_mrc'))['price_mrc__min'] or 0
            meta_tags = self.get_meta_tags('Category', 'catalogue', category_temp.values()[0], min_price_seo,
                                           count_products)

            ids = Product.objects.values_list('categories__id', flat=True).distinct()
            exists_categories = Category.objects.filter(id__in=ids)
            current_ids = list(exists_categories.get_ancestors().values_list('id', flat=True).filter(level=3))
            parent_ids = list(exists_categories.values_list('id', flat=True).filter(level=3))
            all_ids = current_ids + parent_ids
            # category_three = Category.objects.filter(id__in=all_ids)

            return render(request, self.template_parent_name, {
                'category': self.category,
                'brands_filter': brands,
                'meta_tags': meta_tags,
                'all_ids': all_ids,
                'page_type': page_type,
            })
        else:
            page_type = 'Список товаров'
            if url_seo:
                categories_ids = list(self.category.get_descendants().values_list('id', flat=True).exclude(is_accessory=True))
                categories_ids.append(self.category.pk)
                # categories_ids.append(self.category.id)
                # for cat in categories:
                #     descendants = cat.get_descendants()
                #     if descendants:
                #         c_ids_with_products = descendants
                #         if self.category.is_accessory:
                #             for c_id in c_ids_with_products:
                #                 if c_id.id not in categories_ids:
                #                     categories_ids.append(c_id.id)
                #         else:
                #             for c_id in c_ids_with_products:
                #                 if not c_id.is_accessory and not c_id.parent.is_accessory:
                #                     if c_id.id not in categories_ids:
                #                         categories_ids.append(c_id.id)

                # categories_list = self.category.get_family().filter(level=2) if self.category.level > 1 else [self.category]
                if self.category.level > 2:
                    categories_list = self.category.get_family().filter(level=2).first().get_children()
                else:
                    categories_list = self.category.get_children()
                categories_list_result = categories_list

                print("///////////////////////")
                print(categories_ids)
                print("///////////////////////")
                products_stock = Product.objects. \
                    filter(Q(categories__in=categories_ids),
                           Q(is_show=True),
                           Q(num_in_stock__gt=0),
                           Q(num_in_stock__gt=F('num_allocated'))). \
                    order_by('-date_created')

                products_unstock = Product.objects. \
                    filter(Q(categories__in=categories_ids),
                           Q(is_show=True),
                           (Q(num_in_stock=0) |
                            Q(num_in_stock=F('num_allocated')))). \
                    order_by('-date_created')

                full_max_price_slider = Product.objects.filter(Q(categories__in=categories_ids),Q(is_show=True)).\
                                aggregate(Max('price_mrc'))['price_mrc__max'] or 0

                codes = [k for k, v in description_array.items() if k != 'category']
                attributes = ProductAttribute.objects.filter(code__in=codes)

                seo_attributes = dict()
                for k, v in description_array.items():
                    if k != 'category':
                        att = attributes.get(code=k)
                        att_type = att.type
                        if att_type == 'option':
                            if k != 'age_from' and k != 'age_to':
                                seo_attributes[k] = v
                                products_stock = products_stock.filter(attribute_values__attribute__code=k,
                                                                       attribute_values__value_option__option=v)
                                products_unstock = products_unstock.filter(attribute_values__attribute__code=k,
                                                                           attribute_values__value_option__option=v)
                            else:
                                seo_attributes[k] = v
                                products_stock = products_stock.filter(attribute_values__attribute__code=k,
                                                                       attribute_values__value_option__show_value=v)
                                products_unstock = products_unstock.filter(attribute_values__attribute__code=k,
                                                                           attribute_values__value_option__show_value=v)

                        elif att_type == 'boolean':
                            products_stock = products_stock.filter(attribute_values__attribute__code=k,
                                                                   attribute_values__value_boolean=v)
                            products_unstock = products_unstock.filter(attribute_values__attribute__code=k,
                                                                       attribute_values__value_boolean=v)
                        elif att_type == 'text':
                            products_stock = products_stock.filter(attribute_values__attribute__code=k,
                                                                   attribute_values__value_text=v)
                            products_unstock = products_unstock.filter(attribute_values__attribute__code=k,
                                                                       attribute_values__value_text=v)
                        elif att_type == 'float':
                            products_stock = products_stock.filter(attribute_values__attribute__code=k,
                                                                   attribute_values__value_float=v)
                            products_unstock = products_unstock.filter(attribute_values__attribute__code=k,
                                                                       attribute_values__value_float=v)
                        elif att_type == 'date':
                            products_stock = products_stock.filter(attribute_values__attribute__code=k,
                                                                   attribute_values__value_date=v)
                            products_unstock = products_unstock.filter(attribute_values__attribute__code=k,
                                                                       attribute_values__value_date=v)
                        elif att_type == 'integer':
                            products_stock = products_stock.filter(attribute_values__attribute__code=k,
                                                                   attribute_values__value_integer=v)
                            products_unstock = products_unstock.filter(attribute_values__attribute__code=k,
                                                                       attribute_values__value_integer=v)
                        else:
                            products_stock = products_stock.filter(attribute_values__attribute__code=k,
                                                                   attribute_values__value_text=v)
                            products_unstock = products_unstock.filter(attribute_values__attribute__code=k,
                                                                       attribute_values__value_text=v)

                # print("============================")
                print(products_stock.query)
                # print(products_stock.count())
                # print("============================")
                # print(products_unstock.query)
                # print(products_unstock.count())

                products_list_result = list(chain(products_stock, products_unstock))

                min_price_stock = products_stock.aggregate(Min('price_mrc'))['price_mrc__min'] or -1
                min_price_unstock = products_unstock.aggregate(Min('price_mrc'))['price_mrc__min'] or -1
                max_price_stock = products_stock.aggregate(Max('price_mrc'))['price_mrc__max'] or 0
                max_price_unstock = products_unstock.aggregate(Max('price_mrc'))['price_mrc__max'] or 0
                if min_price_stock == -1:
                    min_price = 0 if min_price_unstock == -1 else min_price_unstock
                else:
                    min_price = min_price_stock
                max_price = max_price_stock if max_price_stock > max_price_unstock else max_price_unstock
                min_price_seo = min_price

                page = self.request.GET.get('page', None)
                limit = self.request.GET.get('limit', 30)

                count_products = len(products_list_result)
                paginator = Paginator(products_list_result, limit)
                try:
                    products = paginator.page(page)
                except PageNotAnInteger:
                    products = paginator.page(1)
                except EmptyPage:
                    products = paginator.page(paginator.num_pages)

                item_ids = []
                product_ids = []

                for p in products:
                    item_ids.append(p.item_id)

                for p in products_list_result:
                    product_ids.append(p.id)

                stock_info = self.get_stock_info_seo(products)

                filter_options = ProductAttributeValue.objects.values_list('attribute_id', 'value_option_id'). \
                    filter(Q(product__categories__in=categories_ids),
                           Q(value_option_id__isnull=False),
                           Q(attribute__is_show=True)).order_by('attribute__display_order')

                filter_value_range = ProductAttributeValue.objects.values('attribute_id'). \
                    annotate(min_value=Min('value_float'), max_value=Max('value_float')). \
                    filter(Q(value_float__isnull=False),
                           Q(product__categories__in=categories_ids),
                           Q(attribute__is_show=True)).order_by('attribute__display_order')

                filter_result = self.get_filter_result(filter_options)
                filter_float_result = dict()
                for fr in filter_value_range:
                    filter_float_result[fr.get('attribute_id')] = [fr.get('min_value'), fr.get('max_value')]

                meta_tags = self.get_meta_tags('Seo', url_seo, categories_for_seo, min_price_seo, count_products)
                links = url_seo.links
                if url_seo.similar_products:
                    similar_products = Product.objects.filter(id__in=url_seo.similar_products)
                else:
                    similar_products = Product.objects.none()

                active_filter_options = ProductAttributeValue.objects.values_list('attribute_id', 'value_option_id'). \
                    filter(Q(product__id__in=product_ids),
                           Q(value_option_id__isnull=False),
                           Q(attribute__is_show=True))

                active_filter_value_range = ProductAttributeValue.objects.values('attribute_id'). \
                    annotate(min_value=Min('value_float'), max_value=Max('value_float')). \
                    filter(Q(value_float__isnull=False),
                           Q(product__id__in=product_ids),
                           Q(attribute__is_show=True))

                active_filter_result = OrderedDict()
                active_float_result = OrderedDict()

                attribute_codes = set()
                for f_opt in active_filter_options:
                    active_current_ids = active_filter_result.get(f_opt[0], set())
                    active_current_ids.add(str(f_opt[1]))
                    active_filter_result[f_opt[0]] = active_current_ids
                    attribute_codes.add(f_opt[0])
                for key, val in active_filter_result.items():
                    active_filter_result[key] = list(val)

                for fr in active_filter_value_range:
                    active_float_result[fr.get('attribute_id')] = [fr.get('min_value'), fr.get('max_value')]
                    attribute_codes.add(fr.get('atttribute_id'))

                if self.category.level == 2:
                    show_attributes = ProductAttribute.objects.filter(id__in=list(attribute_codes))
                else:
                    show_attributes = self.category.attributes.filter(is_show=True)

                response = render(request, 'catalogue/category_url_seo.html', {
                    'category': self.category,
                    'categories': categories_list,
                    'products': products,
                    'min_price': min_price,
                    'max_price': max_price,
                    'max_price_slider': max_price,
                    'seo_attributes': seo_attributes,
                    'parent_category': self.get_parent_category_name(self.category),
                    'categories_ids': categories_ids,
                    'categories_filter': categories_list_result,
                    'all_variants': self.get_all_variants(item_ids),
                    'stock_yes': stock_info.get('stock_yes'),
                    'unstock_yes': stock_info.get('unstock_yes'),
                    'stock_count': stock_info.get('stock_count'),
                    'meta_tags': meta_tags,
                    'filter_options': filter_options,
                    'filter_result': filter_result,
                    'filter_float_result': filter_float_result,
                    'count_products': count_products,
                    'url_seo': url_seo,
                    'filter_page': True,
                    'page_type': page_type,
                    'similar_products': similar_products,
                    'active_filter_result': json.dumps(active_filter_result),
                    'active_float_result': json.dumps(active_float_result),
                    'links': links,
                    'show_attributes': show_attributes,
                })
                response.set_cookie('current_prev', request.path)
                return response
            else:
                categories_accessories = list(categories.get_descendants().values_list('id', flat=True). \
                                              filter(Q(is_accessory=True) | Q(parent__is_accessory=True)))
                categories_ids = list(categories.get_descendants().values_list('id', flat=True))

                categories_ids.append(self.category.id)
                if self.category.level > 2:
                    categories_list = self.category.get_family().filter(level=2).first().get_children()
                else:
                    categories_list = self.category.get_children()

                categories_list_result = categories_list

                categories_all = list(self.category.get_descendants().values_list('id', flat=True))
                categories_all.append(self.category.pk)

                products_list = Product.objects.filter(Q(categories__id__in=categories_all),
                                                       Q(is_show=True),
                                                       Q(num_in_stock__gt=0),
                                                       Q(num_in_stock__gt=F('num_allocated')))

                products_list_result = Product.objects.annotate(stock_status=Case(
                    When(num_in_stock__gt=0, then=1),
                    When(num_in_stock=0, then=2),
                    output_field=IntegerField(),
                )).values('id', 'title', 'slug', 'price_mrc', 'date_created', 'item_id', 'category_name', 'brand_name',
                          'rating', 'slug', 'main_image', 'num_in_stock', 'num_allocated', 'variant_name', 'artikul',
                          'is_discount', 'size_item_id', 'stock_status'). \
                    filter(Q(is_show=True),
                           Q(categories__id__in=categories_all),
                           Q(images__display_order=0)).order_by('stock_status', 'categories__is_accessory')

                if categories_accessories:
                    min_price_all = products_list.aggregate(Min('price_mrc'))['price_mrc__min'] or 0
                    max_price_all = products_list.aggregate(Max('price_mrc'))['price_mrc__max'] or 0
                    product_list_accessory = Product.objects.filter(Q(categories__id__in=categories_accessories),
                                                                    Q(is_show=True),
                                                                    Q(num_in_stock__gt=0),
                                                                    Q(num_in_stock__gt=F('num_allocated')))
                    min_price_access = product_list_accessory.aggregate(Min('price_mrc'))['price_mrc__min'] or 0
                    max_price_access = product_list_accessory.aggregate(Max('price_mrc'))['price_mrc__max'] or 0
                    min_price = min_price_all if min_price_all < min_price_access else min_price_access
                    max_price = max_price_all if max_price_all > max_price_access else max_price_access
                    if self.category.is_accessory:
                        min_price_seo = min_price_all if min_price_all < min_price_access else min_price_access
                    else:
                        min_price_seo = products_list.exclude(categories__id__in=categories_accessories).aggregate(Min('price_mrc'))['price_mrc__min'] or 0
                        max_price = max_price_all if max_price_all > max_price_access else max_price_access
                    max_price_slider = max_price
                else:
                    max_price_slider = Product.objects.filter(Q(categories__id__in=categories_all),
                                                              Q(price_mrc__gte=0),
                                                              Q(is_show=True)). \
                                           aggregate(Max('price_mrc'))['price_mrc__max'] or 0

                    min_price_seo = products_list.aggregate(Min('price_mrc'))['price_mrc__min'] or 0
                    min_price = products_list.aggregate(Min('price_mrc'))['price_mrc__min'] or 0
                    max_price = products_list.aggregate(Max('price_mrc'))['price_mrc__max'] or 0

                page = self.request.GET.get('page', None)
                limit = self.request.GET.get('limit', 30)
                count_products = products_list_result.count()
                paginator = Paginator(products_list_result, limit)
                try:
                    products = paginator.page(page)
                except PageNotAnInteger:
                    products = paginator.page(1)
                except EmptyPage:
                    products = paginator.page(paginator.num_pages)
                now_today = timezone.now()
                active_discount = Discount.objects.filter(start_datetime__lte=now_today,
                                                          end_datetime__gte=now_today).first()
                discount_value = None
                discount_ids = []
                # if active_discount:
                #     discount_value = active_discount.discount_value
                #     product_ids = [p.id for p in products]
                #     discount_ids = list(
                #         active_discount.products.filter(id__in=product_ids).values_list('id', flat=True))

                stock_info = self.get_stock_info(products)
                item_ids = [p.get('item_id') for p in products]

                filter_options = ProductAttributeValue.objects.values_list('value_option_id', flat=True). \
                    filter(Q(product__categories__id__in=categories_all),
                           Q(value_option_id__isnull=False))

                in_filter_options = ProductAttributeValue.objects.values_list('attribute_id', 'value_option_id'). \
                    filter(Q(product__categories__id__in=categories_all),
                           Q(value_option_id__isnull=False))
                filter_result = self.get_filter_result(in_filter_options)

                filter_value_range = ProductAttributeValue.objects.values('attribute_id'). \
                    annotate(min_value=Min('value_float'), max_value=Max('value_float')). \
                    filter(Q(value_float__isnull=False),
                           Q(product__categories__id__in=categories_all))

                filter_float_result = dict()
                for fr in filter_value_range:
                    filter_float_result[fr.get('attribute_id')] = [fr.get('min_value'), fr.get('max_value')]

                meta_tags = self.get_meta_tags('Category', 'catalogue', categories_for_seo, min_price_seo,
                                               count_products)

                end = datetime.datetime.now()
                print("Result", end - begin)
                parent_category = self.get_parent_category_name(self.category)
                response = render(request, self.template_name, {
                    'category': self.category,
                    'categories': categories_list,
                    'products': products,
                    'min_price': min_price,
                    'max_price': max_price,
                    'max_price_slider': max_price_slider,
                    'categories_ids': categories_ids,
                    'categories_filter': categories_list_result,
                    'all_variants': self.get_all_variants(item_ids),
                    'stock_yes': stock_info.get('stock_yes'),
                    'unstock_yes': stock_info.get('unstock_yes'),
                    'meta_tags': meta_tags,
                    'filter_options': filter_options,
                    'filter_result': filter_result,
                    'filter_float_result': filter_float_result,
                    'count_products': count_products,
                    'url_seo': url_seo,
                    'parent_category': parent_category,
                    'discount_value': discount_value,
                    'discount_ids': discount_ids,
                    'page_type': page_type,
                })
                response.set_cookie('current_prev', request.path)
                return response


class CommonMethodMixin(object):
    def dictfetchall(self, cursor):
        columns = [col[0] for col in cursor.description]
        return [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]

    def namedtuplefetchall(self, cursor):
        nt_result = namedtuple('Result', [col[0] for col in cursor.description])
        return [nt_result(*row) for row in cursor.fetchall()]


class ProductCategoryAjaxView(CommonMethodMixin, View):
    """Работа фильтра на всех страницах сайта где есть фильтр"""

    def create_sql_query(self, sql_where, count_params):
        sql_group_having = 'GROUP BY product_id  HAVING COUNT(*)={0}'.format(count_params)
        sql = '''SELECT product_id  FROM catalogue_productattributevalue WHERE ({0}) {1}'''.format(sql_where,
                                                                                                   sql_group_having)
        return sql

    def get_filter_result(self, filter_options):
        filter_result = OrderedDict()
        for f_opt in filter_options:
            current_ids = filter_result.get(f_opt[0], set())
            current_ids.add(f_opt[1])
            filter_result[f_opt[0]] = current_ids

        for key, val in filter_result.items():
            filter_result[key] = list(val)
        return filter_result

    def get_attribute_options_product(self, attr, attr_param, min_price, max_price):
        current_products = set(ProductAttributeValue.objects.values_list('product_id', flat=True). \
                               filter(attribute__id=attr.id,
                                      value_option_id__in=attr_param,
                                      product__price_mrc__gte=min_price,
                                      product__price_mrc__lte=max_price
                                      ))
        return current_products

    def get_attribute_float_product(self, attr_code, min_val, max_val, min_price, max_price):
        current_products = set(ProductAttributeValue.objects.values_list('product_id', flat=True). \
                               filter(attribute__code=attr_code,
                                      value_float__gte=min_val,
                                      value_float__lte=max_val,
                                      product__price_mrc__gte=min_price,
                                      product__price_mrc__lte=max_price
                                      ))
        return current_products

    def get_ids_without_last_filter(self, sql_where, params):
        sql_where = sql_where.strip()
        if sql_where.endswith('OR'):
            sql_where = sql_where[:-2]
        cursor = connection.cursor()
        sql = self.create_sql_query(sql_where, len(params))
        cursor.execute(sql, params)
        res = self.dictfetchall(cursor)
        product_ids = [r.get('product_id') for r in res]
        return product_ids

    def get_all_variants(self, item_ids):
        all_variants = Product.objects.values('pk', 'item_id', 'title', 'main_image'). \
            filter(Q(item_id__in=item_ids),
                   Q(is_show=True),
                   Q(num_in_stock__gt=0),
                   Q(num_in_stock__gt=F('num_allocated'))). \
            exclude(item_id=None)
        return all_variants

    def get(self, request, *args, **kwargs):
        category_id = request.GET.get('category')
        category_change = request.GET.get('category_change')
        page_load = request.GET.get('page_load')
        attributes_order = request.GET.get('attr-orders', '')
        search_phrase = request.GET.get('search-phrase')
        sales = request.GET.get('sales')
        brand_page = request.GET.get('brand_page')
        # Если в меню выбрана категория, то берем её подкатегории
        if category_id:
            category = Category.objects.filter(id=category_id).first()
            categories_ids = list(category.get_descendants().values_list('id', flat=True)) if category else []
            categories_ids.append(category_id)
        else:
            categories_ids = []
            category = None

        if sales or search_phrase or brand_page:
            # Для страницы с акциями, брендами, поиском выводим основные аттрибуты в фильтре
            main_attributes = ProductAttribute.objects.filter(is_main=True)
        else:
            main_attributes = None

        attributes_order_data = [attr_o for attr_o in attributes_order.split(',') if attr_o]
        last_order_attr = int(attributes_order_data[-1].split(':')[0]) if attributes_order_data else None

        min_price = request.GET.get('price-slider-min', 0)
        max_price_product_info = Product.objects.aggregate(max_price=Max('price_mrc'))
        max_price_product = max_price_product_info.get('max_price')
        max_price = request.GET.get('price-slider-max', max_price_product)
        product_ids = set()
        sql_where_without_last = ''
        params_without_last = []
        options_data = dict()
        c = 0
        if not category_change:
            not_attributes = True
            print('ProductAttribute.objects.filter(is_show=True) === ', ProductAttribute.objects.filter(is_show=True))
            for attr in ProductAttribute.objects.filter(is_show=True):
                attr_param_new = request.GET.get(attr.code)

                if attr_param_new:
                    not_attributes = False
                    c += 1
                    attr_param = [at for at in attr_param_new.split(',') if at]
                    current_products = self.get_attribute_options_product(attr, attr_param, min_price, max_price)
                    product_ids = product_ids | current_products if c == 1 else product_ids & current_products
                    if last_order_attr != attr.id:
                        params_without_last.append(tuple(attr_param))
                        sql_where_without_last += '(attribute_id={0} AND value_option_id IN %s ) OR '.format(attr.id)

            slider_attributes = OrderedDict()
            for k, v in request.GET.items():
                if k in ['price-slider-max', 'price-slider-min']:
                    continue
                if '-slider' in k:
                    attr = k.replace('-slider-min', '').replace('-slider-max', '')
                    if attr not in slider_attributes:
                        slider_attributes[attr] = {}
                    if '-slider-min' in k:
                        slider_attributes[attr]['min_val'] = v
                    elif '-slider-max' in k:
                        slider_attributes[attr]['max_val'] = v
            for k, v in slider_attributes.items():
                current_products = self.get_attribute_float_product(k, v.get('min_val'), v.get('max_val'), min_price,
                                                                    max_price)

                if not not_attributes:
                    product_ids = product_ids & current_products
                else:
                    not_attributes = False
                    product_ids = product_ids | current_products

        else:
            not_attributes = True

        # Если нет аттрибутов (страница брендов, акций и поиска)

        # Если фильтруем на странице Акций
        if sales:
            # Берем все акции, действующие акции на данный момент времени
            now_date = timezone.now()
            current_discounts = Discount.objects.filter(start_datetime__lte=now_date,
                                                        end_datetime__gte=now_date)
            # Берем товары, которые участвуют в акциях
            current_discounts_products_ids = set()
            for current_discount in current_discounts:
                current_discounts_products_temp = current_discount.products.all()
                # Берем id товаров и избавляемся от дублирующихся товаров
                for prod in current_discounts_products_temp:
                    current_discounts_products_ids.add(prod.id)

            # Берем только те товары, что есть в наличие
            products_stock = Product.objects.filter(Q(id__in=current_discounts_products_ids), Q(is_show=True),
                                                    Q(num_in_stock__gt=0),
                                                    Q(num_in_stock__gt=F('num_allocated')))
            products_unstock = []

        else:
            products_stock = Product.objects.filter(Q(is_show=True),
                                                    Q(num_in_stock__gt=0),
                                                    Q(num_in_stock__gt=F('num_allocated')))

            products_unstock = Product.objects.filter(Q(is_show=True),
                                                      (Q(num_in_stock=0) |
                                                       Q(num_in_stock=F('num_allocated'))))
        if not_attributes is False:
            products_stock = products_stock.filter(Q(id__in=product_ids))
            if products_unstock:
                products_unstock = products_unstock.filter(Q(id__in=product_ids))
            if categories_ids:
                products_stock = products_stock.filter(Q(categories__id__in=categories_ids))
                if products_unstock:
                    products_unstock = products_unstock.filter(Q(categories__id__in=categories_ids))
            if search_phrase:
                products_stock = products_stock.filter(Q(title__icontains='' + search_phrase + '') |
                                                       Q(artikul__icontains='' + search_phrase + ''))
                if products_unstock:
                    products_unstock = products_unstock.filter(Q(title__icontains='' + search_phrase + '') |
                                                               Q(artikul__icontains='' + search_phrase + ''))
        else:
            if categories_ids:
                products_stock = products_stock.filter(Q(categories__id__in=categories_ids))
                if products_unstock:
                    products_unstock = products_unstock.filter(Q(categories__id__in=categories_ids))

            products_stock = products_stock.filter(Q(price_mrc__lte=max_price),
                                                   Q(price_mrc__gte=min_price))
            if products_unstock:
                products_unstock = products_unstock.filter(Q(price_mrc__lte=max_price),
                                                           Q(price_mrc__gte=min_price))
            if search_phrase:
                products_stock = products_stock.filter(Q(title__icontains='' + search_phrase + '') |
                                                       Q(artikul__icontains='' + search_phrase + ''))
                if products_unstock:
                    products_unstock = products_unstock.filter(Q(title__icontains='' + search_phrase + '') |
                                                               Q(artikul__icontains='' + search_phrase + ''))

        max_price_stock = products_stock.aggregate(Max('price_mrc'))['price_mrc__max'] or 0
        if products_unstock:
            max_price_unstock = products_unstock.aggregate(Max('price_mrc'))['price_mrc__max'] or 0
        else:
            max_price_unstock = 0
        max_price_slider = max_price_stock if max_price_stock > max_price_unstock else max_price_unstock
        sort = request.GET.get('sort')
        if sort:
            products_stock = products_stock.order_by(sort)
            if products_unstock:
                products_unstock = products_unstock.order_by(sort)
        else:
            products_stock = products_stock.order_by('categories__is_accessory', '-date_created')
            if products_unstock:
                products_unstock = products_unstock.order_by('categories__is_accessory', '-date_created')

        products = list(chain(products_stock, products_unstock))
        count_products = len(products)
        page = request.GET.get('page')
        page_size = request.GET.get('pagesize', 30)
        paginator = Paginator(products, page_size)
        try:
            products = paginator.page(page)
        except PageNotAnInteger:
            products = paginator.page(1)
        except EmptyPage:
            products = paginator.page(paginator.num_pages)

        item_ids = [p.item_id for p in products]
        all_variants = self.get_all_variants(item_ids)

        stock_yes, unstock_yes = False, False
        stock_count = 0
        for p in products:
            if p.num_in_stock > 0:
                stock_yes = True
                stock_count +=1
            if p.num_in_stock == 0:
                unstock_yes = True

        now_today = timezone.now()
        active_discount = Discount.objects.filter(start_datetime__lte=now_today, end_datetime__gte=now_today).first()
        discount_value = None
        discount_ids = []
        if active_discount:
            discount_value = active_discount.discount_value
            temp_product_ids = [p.id for p in products]
            discount_ids = list(active_discount.products.filter(id__in=temp_product_ids).values_list('id', flat=True))

        data = dict()
        data['status'] = 'ok'

        filter_result, filter_float_result, filter_last_result = {}, {}, {}

        if product_ids:
            print("product_ids filter options")
            filter_options = ProductAttributeValue.objects.values_list('attribute_id', 'value_option_id'). \
                filter(Q(product__id__in=product_ids),
                       Q(product__price_mrc__gte=min_price),
                       Q(product__price_mrc__lte=max_price),
                       Q(value_option_id__isnull=False),
                       Q(attribute__is_show=True))

            filter_value_range = ProductAttributeValue.objects.values('attribute_id'). \
                annotate(min_value=Min('value_float'), max_value=Max('value_float')). \
                filter(Q(value_float__isnull=False),
                       Q(product__id__in=product_ids),
                       Q(product__price_mrc__gte=min_price),
                       Q(product__price_mrc__lte=max_price),
                       Q(attribute__is_show=True))

            if categories_ids:
                filter_options = filter_options.filter(Q(product__categories__id__in=categories_ids))
                filter_value_range = filter_value_range.filter(Q(product__categories__id__in=categories_ids))

            filter_options = filter_options.distinct().order_by('attribute__display_order')
            filter_value_range = filter_value_range.order_by('attribute__display_order')

            if sql_where_without_last and params_without_last:
                product_without_last_ids = self.get_ids_without_last_filter(sql_where_without_last, params_without_last)

                filter_last_options = ProductAttributeValue.objects.values_list('attribute_id', 'value_option_id'). \
                    filter(Q(product__price_mrc__gte=min_price),
                           Q(product_id__in=product_without_last_ids),
                           Q(product__price_mrc__lte=max_price),
                           Q(attribute__is_show=True)).order_by('attribute__display_order')
            else:
                filter_last_options = []
        else:
            # Если в отправляемых с фильтра параметрах была категория
            if categories_ids:
                # Если есть поисковая фраза
                if search_phrase:
                    filter_options = ProductAttributeValue.objects.values_list('attribute_id', 'value_option_id'). \
                        filter(Q(product__categories__in=categories_ids),
                               (Q(product__title__icontains='' + search_phrase + '') |
                                Q(product__artikul__icontains='' + search_phrase + '')),
                               Q(value_option_id__isnull=False),
                               Q(product__price_mrc__gte=min_price),
                               Q(product__price_mrc__lte=max_price),
                               Q(attribute__is_show=True)).order_by('attribute__display_order')

                    filter_value_range = ProductAttributeValue.objects.values('attribute_id'). \
                        annotate(min_value=Min('value_float'), max_value=Max('value_float')). \
                        filter(Q(value_float__isnull=False),
                               (Q(product__title__icontains='' + search_phrase + '') |
                                Q(product__artikul__icontains='' + search_phrase + '')),
                               Q(product__price_mrc__gte=min_price),
                               Q(product__price_mrc__lte=max_price),
                               Q(product__categories__in=categories_ids),
                               Q(attribute__is_show=True)).order_by('attribute__display_order')
                else:
                    filter_options = ProductAttributeValue.objects.values_list('attribute_id', 'value_option_id'). \
                        filter(Q(product__categories__in=categories_ids),
                               Q(value_option_id__isnull=False),
                               Q(product__price_mrc__gte=min_price),
                               Q(product__price_mrc__lte=max_price),
                               Q(attribute__is_show=True)).order_by('attribute__display_order')

                    filter_value_range = ProductAttributeValue.objects.values('attribute_id'). \
                        annotate(min_value=Min('value_float'), max_value=Max('value_float')). \
                        filter(Q(value_float__isnull=False),
                               Q(product__price_mrc__gte=min_price),
                               Q(product__price_mrc__lte=max_price),
                               Q(product__categories__in=categories_ids),
                               Q(attribute__is_show=True)).order_by('attribute__display_order')
                filter_last_options = []
            # Если с фильтра не была отправлена категория, обычно это на страницах поиска, брендов и акций,
            # так как там нет определенной категории
            else:
                # Если есть поисковая фраза
                if search_phrase:
                    filter_options = ProductAttributeValue.objects.values_list('attribute_id', 'value_option_id'). \
                        filter((Q(product__title__icontains='' + search_phrase + '') |
                                Q(product__artikul__icontains='' + search_phrase + '')),
                               Q(value_option_id__isnull=False),
                               Q(product__price_mrc__gte=min_price),
                               Q(product__price_mrc__lte=max_price),
                               Q(attribute__is_show=True)).order_by('attribute__display_order')

                    filter_value_range = ProductAttributeValue.objects.values('attribute_id'). \
                        annotate(min_value=Min('value_float'), max_value=Max('value_float')). \
                        filter(Q(value_float__isnull=False),
                               (Q(product__title__icontains='' + search_phrase + '') |
                                Q(product__artikul__icontains='' + search_phrase + '')),
                               Q(product__price_mrc__gte=min_price),
                               Q(product__price_mrc__lte=max_price),
                               Q(attribute__is_show=True)).order_by('attribute__display_order')

                else:
                    filter_options = ProductAttributeValue.objects.values_list('attribute_id', 'value_option_id'). \
                        filter(Q(value_option_id__isnull=False),
                               Q(product__price_mrc__gte=min_price),
                               Q(product__price_mrc__lte=max_price),
                               Q(attribute__is_show=True)).order_by('attribute__display_order')

                    filter_value_range = ProductAttributeValue.objects.values('attribute_id'). \
                        annotate(min_value=Min('value_float'), max_value=Max('value_float')). \
                        filter(Q(value_float__isnull=False),
                               Q(product__price_mrc__gte=min_price),
                               Q(product__price_mrc__lte=max_price),
                               Q(attribute__is_show=True)).order_by('attribute__display_order')
                filter_last_options = []

        for f_opt in filter_options:
            current_ids = filter_result.get(str(f_opt[0]), set())
            current_ids.add(str(f_opt[1]))
            filter_result[str(f_opt[0])] = current_ids
        for key, val in filter_result.items():
            filter_result[key] = list(val)

        for fl_opt in filter_last_options:
            l_current_ids = filter_last_result.get(str(fl_opt[0]), set())
            l_current_ids.add(str(fl_opt[1]))
            filter_last_result[str(fl_opt[0])] = l_current_ids
        for k, v in filter_last_result.items():
            filter_last_result[k] = list(v)

        for fr in filter_value_range:
            filter_float_result[fr.get('attribute_id')] = [fr.get('min_value'), fr.get('max_value')]

        data['filter_options'] = json.dumps(filter_result)
        data['filter_float_options'] = json.dumps(filter_float_result)
        data['filter_last_options'] = json.dumps(filter_last_result)

        if category_change or page_load:
            in_filter_options = ProductAttributeValue.objects.values_list('attribute_id', 'value_option_id'). \
                filter(Q(product__categories__in=categories_ids),
                       Q(value_option_id__isnull=False))

            filter_result = self.get_filter_result(in_filter_options)

            filter_value_range = ProductAttributeValue.objects.values('attribute_id'). \
                annotate(min_value=Min('value_float'), max_value=Max('value_float')). \
                filter(Q(value_float__isnull=False),
                       Q(product__categories__in=categories_ids))

            filter_float_result = dict()
            for fr in filter_value_range:
                filter_float_result[fr.get('attribute_id')] = [fr.get('min_value'), fr.get('max_value')]

            options_data['filter_result'] = filter_result
            options_data['filter_float_result'] = filter_float_result

        data['products'] = products
        data['discount_ids'] = discount_ids
        data['discount_value'] = discount_value
        data['paginator'] = paginator
        data['page_size'] = page_size
        data['count_products'] = count_products
        data['all_variants'] = all_variants
        data['stock_yes'] = stock_yes
        data['unstock_yes'] = unstock_yes
        data['stock_count'] = stock_count

        result = dict()
        if category:
            options_data['category'] = category
        options_data['min_price'] = min_price
        options_data['max_price'] = max_price
        options_data['max_price_slider'] = max_price

        if request.GET.get('url_seo'):
            url_seo = SeoModuleFilterUrls.objects.filter(pk=request.GET.get('url_seo')).first()
            data['url_seo'] = url_seo
            html = render_to_string("catalogue/partials/product_ajax_seo_filter.html", data, request=request)
        else:
            html = render_to_string("catalogue/partials/product_ajax_filter.html", data, request=request)

        if category_change or page_load:
            if main_attributes:
                options_data['main_attributes'] = main_attributes
                if sales:
                    options_data['page'] = 'sales'
                elif search_phrase:
                    options_data['page'] = 'search_page'
                elif brand_page:
                    options_data['page'] = 'brand'

                html_options = render_to_string("catalogue/partials/options_ajax_filter_brand_search.html",
                                                options_data,
                                                request=request)
            else:
                html_options = render_to_string("catalogue/partials/options_ajax_filter.html", options_data,
                                                request=request)
            result['options_html'] = html_options

        result['html'] = html
        return HttpResponse(json.dumps(result), content_type='application/json')
        # return HttpResponse(html)


class SearchPageView(CommonFilterGetDataMixin, View):
    template_name = 'catalogue/search_results.html'

    def get_categories_products(self, categories_ids):
        full_categories_ids = []
        category_all = Category.objects.select_related('parent').filter(pk__in=categories_ids)
        products_all = Product.objects.prefetch_related('categories').filter(
            Q(num_in_stock__gt=F('num_allocated')), Q(num_in_stock__gt=0),
            Q(categories__in=category_all))
        for id in categories_ids:
            category = category_all.get(pk=id)
            category_childs = category.get_children()
            if category_childs:
                j = len(category_childs)
                count = j
                for c_sub in category_childs:
                    products = products_all.filter(Q(categories=c_sub.id))
                    if products and len(products) > 0:
                        j -= 1
                if j < count:
                    full_categories_ids.append(category.id)
            else:
                products = products_all.filter(Q(categories=id))
                if products and len(products) > 0:
                    full_categories_ids.append(id)
        if len(full_categories_ids) > 0:
            categories_with_products = category_all.filter(pk__in=full_categories_ids).order_by('lft')
        else:
            categories_with_products = ''
        return categories_with_products

    def get_all_variants(self, item_ids):
        all_variants = Product.objects.values('pk', 'item_id', 'title', 'main_image'). \
            filter(Q(item_id__in=item_ids),
                   Q(is_show=True),
                   Q(num_in_stock__gt=0),
                   Q(num_in_stock__gt=F('num_allocated'))). \
            exclude(item_id=None)
        return all_variants

    def get(self, request, *args, **kwargs):
        start = datetime.datetime.now()

        search_phrase = request.GET.get('search_phrase', None)
        if search_phrase:
            search_phrase = search_phrase.strip()
            categories_temp = Category.objects.filter(name__icontains='' + search_phrase + '')

            categories_ids = []
            for cat in categories_temp:
                category_child = Category.objects.prefetch_related('children').get(pk=cat.pk)
                categories_child = category_child.get_children()
                for cat_c in categories_child:
                    categories_ids.append(cat_c.id)
                    category_child_lower = Category.objects.prefetch_related('children').get(pk=cat_c.pk)
                    categories_child_lower = category_child_lower.get_children()
                    for cat_c_l in categories_child_lower:
                        categories_ids.append(cat_c_l.id)
                categories_ids.append(category_child.id)

            print('======', categories_ids)

            categories_ids_with_products = Category.objects.filter(id__in=categories_ids)
            print(categories_ids_with_products)

            products_stock = Product.objects.filter((Q(categories__in=categories_ids_with_products) |
                                                     (Q(title__icontains='' + search_phrase + '') |
                                                      Q(artikul__icontains='' + search_phrase + ''))),
                                                    Q(num_in_stock__gt=0),
                                                    Q(num_in_stock__gt=F('num_allocated'))
                                                    ).order_by('-date_created').distinct()

            products_unstock = Product.objects.filter((Q(categories__in=categories_ids_with_products) |
                                                       (Q(title__icontains='' + search_phrase + '') |
                                                        Q(artikul__icontains='' + search_phrase + ''))),
                                                      (Q(num_in_stock=0) |
                                                       Q(num_in_stock=F('num_allocated')))
                                                      ).order_by('-date_created').distinct()

            max_price_stock = products_stock.aggregate(Max('price_mrc')).get('price_mrc__max') or 0
            max_price_unstock = products_unstock.aggregate(Max('price_mrc')).get('price_mrc__max') or 0
            results = list(chain(products_stock, products_unstock))
            print("results",results)
            product_ids = [p.id for p in results]

            categories_list = []

            if categories_ids:
                categories = Category.objects.filter(pk__in=categories_ids_with_products)
                categories_list = categories_ids_with_products
                categories_list_data = [cat.pk for cat in categories_list]
            elif categories_temp:
                categories = categories_temp
                for cat in categories:
                    categories_list = categories_list.append(cat.pk)
                categories_list_data = categories_list
            else:
                print("CaT ID")
                # cat_id = []
                cat_id = Product.objects.values_list('categories__id', flat=True). \
                    filter(id__in=product_ids)
                categories = Category.objects.filter(pk__in=cat_id)
                categories_list = cat_id
                categories_list_data = categories_list

            for cat in categories:
                print('cat.parent.name===', cat.parent.name)
                if cat.get_children() or cat.name.find("Аксессуары") != -1:
                    print('cat.name===', cat.name)
                    categories = categories.exclude(pk=cat.pk)

            min_price = 0
            max_price = max_price_stock if max_price_stock > max_price_unstock else max_price_unstock

            filter_options = ProductAttributeValue.objects.values_list('attribute_id', 'value_option_id'). \
                filter(Q(product_id__in=product_ids),
                       Q(attribute__is_show=True)).order_by('attribute__display_order')

            filter_result = self.get_filter_result(filter_options)
            main_attributes = ProductAttribute.objects.filter(is_main=True)
            pages = Paginator(results, 30)
            try:
                products = pages.page(1)
            except PageNotAnInteger:
                products = pages.page(1)
            except EmptyPage:
                products = pages.page(pages.num_pages)
            brands_filter = []

            item_ids = [p.item_id for p in products]
            all_variants = self.get_all_variants(item_ids)
            count_products = len(results)
            stock_yes, unstock_yes = False, False
            for p in products:
                if p.num_in_stock > 0 and p.num_in_stock > p.num_allocated:
                    stock_yes = True
                if p.num_in_stock == 0 or p.num_in_stock == p.num_allocated:
                    unstock_yes = True
            search_phrase_empty = False
        else:
            products = Product.objects.none()
            categories = None
            filter_result = None
            main_attributes = None
            stock_yes = False
            unstock_yes = False
            all_variants = None
            max_price = 0
            min_price = 0
            search_phrase_empty = True
            count_products = 0

        ctx = dict()
        ctx['products'] = products
        ctx['categories'] = categories
        ctx['min_price'] = min_price
        ctx['max_price'] = max_price
        ctx['max_price_slider'] = max_price
        ctx['search_phrase'] = search_phrase
        ctx['search_phrase_empty'] = search_phrase_empty
        ctx['filter_result'] = filter_result
        ctx['main_attributes'] = main_attributes
        ctx['stock_yes'] = stock_yes
        ctx['unstock_yes'] = unstock_yes
        ctx['count_products'] = count_products
        ctx['all_variants'] = all_variants

        end = datetime.datetime.now()
        res = end - start

        response = render(request, self.template_name, ctx)
        response.set_cookie('current_prev', request.path)
        return response


class BrandSearchAjaxView(CommonMethodMixin, View):
    def create_sql_query(self, sql_where, count_params):
        sql_group_having = 'GROUP BY product_id  HAVING COUNT(*)={0}'.format(count_params)
        sql = '''SELECT product_id  FROM catalogue_productattributevalue WHERE ({0}) {1}'''.format(sql_where,
                                                                                                   sql_group_having)
        return sql

    def get_filter_result(self, filter_options):
        filter_result = OrderedDict()
        for f_opt in filter_options:
            current_ids = filter_result.get(f_opt[0], set())
            current_ids.add(f_opt[1])
            filter_result[f_opt[0]] = current_ids

        for key, val in filter_result.items():
            filter_result[key] = list(val)
        return filter_result

    def get_attribute_options_product(self, attr, attr_param, min_price, max_price):
        current_products = set(ProductAttributeValue.objects.values_list('product_id', flat=True). \
                               filter(attribute__id=attr.id,
                                      value_option_id__in=attr_param,
                                      product__price_mrc__gte=min_price,
                                      product__price_mrc__lte=max_price
                                      ))
        return current_products

    def get_attribute_float_product(self, attr_code, min_val, max_val, min_price, max_price):
        current_products = set(ProductAttributeValue.objects.values_list('product_id', flat=True). \
                               filter(attribute__code=attr_code,
                                      value_float__gte=min_val,
                                      value_float__lte=max_val,
                                      product__price_mrc__gte=min_price,
                                      product__price_mrc__lte=max_price
                                      ))
        return current_products

    def get_ids_without_last_filter(self, sql_where, params):
        sql_where = sql_where.strip()
        if sql_where.endswith('OR'):
            sql_where = sql_where[:-2]
        cursor = connection.cursor()
        sql = self.create_sql_query(sql_where, len(params))
        cursor.execute(sql, params)
        res = self.dictfetchall(cursor)
        product_ids = [r.get('product_id') for r in res]
        return product_ids

    def get_all_variants(self, item_ids):
        all_variants = Product.objects.values('pk', 'item_id', 'title', 'main_image'). \
            filter(Q(item_id__in=item_ids),
                   Q(is_show=True),
                   Q(num_in_stock__gt=0),
                   Q(num_in_stock__gt=F('num_allocated'))). \
            exclude(item_id=None)
        return all_variants

    def get(self, request, *args, **kwargs):
        category_id = request.GET.get('category')
        category_change = request.GET.get('category_change')
        page_load = request.GET.get('page_load')
        attributes_order = request.GET.get('attr-orders', '')
        category = Category.objects.filter(id=category_id).first()
        categories_ids = list(category.get_descendants().values_list('id', flat=True)) if category else []
        categories_ids.append(category_id)

        attributes_order_data = [attr_o for attr_o in attributes_order.split(',') if attr_o]
        last_order_attr = int(attributes_order_data[-1].split(':')[0]) if attributes_order_data else None

        min_price = request.GET.get('price-slider-min', 0)
        max_price_product_info = Product.objects.aggregate(max_price=Max('price_mrc'))
        max_price_product = max_price_product_info.get('max_price')
        max_price = request.GET.get('price-slider-max', max_price_product)
        product_ids = set()
        product_ids_without_last = set()
        sql_where_without_last = ''
        params_without_last = []
        options_data = dict()
        c = 0
        if not category_change:
            not_attributes = True
            for attr in ProductAttribute.objects.filter(is_show=True):
                # attr_param = request.GET.getlist(attr.code)
                attr_param_new = request.GET.get(attr.code)
                if attr_param_new:
                    not_attributes = False
                    c += 1
                    attr_param = [at for at in attr_param_new.split(',') if at]
                    current_products = self.get_attribute_options_product(attr, attr_param, min_price, max_price)
                    product_ids = product_ids | current_products if c == 1 else product_ids & current_products
                    if last_order_attr != attr.id:
                        params_without_last.append(tuple(attr_param))
                        sql_where_without_last += '(attribute_id={0} AND value_option_id IN %s ) OR '.format(attr.id)

            slider_attributes = OrderedDict()
            for k, v in request.GET.items():
                if k in ['price-slider-max', 'price-slider-min']:
                    continue
                if '-slider' in k:
                    attr = k.replace('-slider-min', '').replace('-slider-max', '')
                    if attr not in slider_attributes:
                        slider_attributes[attr] = {}
                    if '-slider-min' in k:
                        slider_attributes[attr]['min_val'] = v
                    elif '-slider-max' in k:
                        slider_attributes[attr]['max_val'] = v
            for k, v in slider_attributes.items():
                current_products = self.get_attribute_float_product(k, v.get('min_val'), v.get('max_val'), min_price,
                                                                    max_price)
                if not not_attributes:
                    product_ids = product_ids & current_products
        else:
            not_attributes = True

        if not_attributes is False:
            products_stock = Product.objects.filter(Q(categories__id__in=categories_ids),
                                                    Q(id__in=product_ids),
                                                    Q(is_show=True),
                                                    Q(num_in_stock__gte=0),
                                                    Q(num_in_stock__gt=F('num_allocated')))

            products_unstock = Product.objects.filter(Q(categories__id__in=categories_ids),
                                                      Q(id__in=product_ids),
                                                      Q(is_show=True),
                                                      (Q(num_in_stock=0) |
                                                       Q(num_in_stock=F('num_allocated'))))
        else:
            products_stock = Product.objects.filter(Q(categories__id__in=categories_ids),
                                                    Q(num_in_stock__gt=0),
                                                    Q(num_in_stock__gt=F('num_allocated')),
                                                    Q(is_show=True),
                                                    Q(price_mrc__lte=max_price),
                                                    Q(price_mrc__gte=min_price))

            products_unstock = Product.objects.filter(Q(categories__id__in=categories_ids),
                                                      (Q(num_in_stock=0) |
                                                       Q(num_in_stock=F('num_allocated'))),
                                                      Q(is_show=True),
                                                      Q(price_mrc__lte=max_price),
                                                      Q(price_mrc__gte=min_price))

        max_price_stock = products_stock.aggregate(Max('price_mrc'))['price_mrc__max'] or 0
        max_price_unstock = products_unstock.aggregate(Max('price_mrc'))['price_mrc__max'] or 0
        max_price_slider = max_price_stock if max_price_stock > max_price_unstock else max_price_unstock
        sort = request.GET.get('sort')
        if sort:
            products_stock = products_stock.order_by(sort)
            products_unstock = products_unstock.order_by(sort)
        else:
            products_stock = products_stock.order_by('categories__is_accessory', '-date_created')
            products_unstock = products_unstock.order_by('categories__is_accessory', '-date_created')

        products = list(chain(products_stock, products_unstock))
        count_products = len(products)
        page = request.GET.get('page')
        page_size = request.GET.get('pagesize', 30)
        paginator = Paginator(products, page_size)
        try:
            products = paginator.page(page)
        except PageNotAnInteger:
            products = paginator.page(1)
        except EmptyPage:
            products = paginator.page(paginator.num_pages)

        item_ids = [p.item_id for p in products]
        all_variants = self.get_all_variants(item_ids)

        stock_yes, unstock_yes = False, False
        for p in products:
            if p.num_in_stock > 0:
                stock_yes = True
            if p.num_in_stock == 0:
                unstock_yes = True

        data = dict()
        data['status'] = 'ok'

        filter_result, filter_float_result, filter_last_result = {}, {}, {}
        if product_ids:
            filter_options = ProductAttributeValue.objects.values_list('attribute_id', 'value_option_id'). \
                filter(Q(product__id__in=product_ids),
                       Q(product__price_mrc__gte=min_price),
                       Q(product__price_mrc__lte=max_price),
                       Q(product__categories__id__in=categories_ids),
                       Q(value_option_id__isnull=False),
                       Q(attribute__is_show=True)).distinct().order_by('attribute__display_order')

            filter_value_range = ProductAttributeValue.objects.values('attribute_id'). \
                annotate(min_value=Min('value_float'), max_value=Max('value_float')). \
                filter(Q(value_float__isnull=False),
                       Q(product__categories__id__in=categories_ids),
                       Q(product__id__in=product_ids),
                       Q(product__price_mrc__gte=min_price),
                       Q(product__price_mrc__lte=max_price),
                       Q(attribute__is_show=True)).order_by('attribute__display_order')
            if sql_where_without_last and params_without_last:
                product_without_last_ids = self.get_ids_without_last_filter(sql_where_without_last, params_without_last)

                filter_last_options = ProductAttributeValue.objects.values_list('attribute_id', 'value_option_id'). \
                    filter(Q(product__price_mrc__gte=min_price),
                           Q(product_id__in=product_without_last_ids),
                           Q(product__price_mrc__lte=max_price),
                           Q(attribute__is_show=True)).order_by('attribute__display_order')
            else:
                filter_last_options = []
        else:
            filter_options = ProductAttributeValue.objects.values_list('attribute_id', 'value_option_id'). \
                filter(Q(product__categories__in=categories_ids),
                       Q(value_option_id__isnull=False),
                       Q(product__price_mrc__gte=min_price),
                       Q(product__price_mrc__lte=max_price),
                       Q(attribute__is_show=True)).order_by('attribute__display_order')

            filter_value_range = ProductAttributeValue.objects.values('attribute_id'). \
                annotate(min_value=Min('value_float'), max_value=Max('value_float')). \
                filter(Q(value_float__isnull=False),
                       Q(product__price_mrc__gte=min_price),
                       Q(product__price_mrc__lte=max_price),
                       Q(product__categories__in=categories_ids),
                       Q(attribute__is_show=True)).order_by('attribute__display_order')
            filter_last_options = []

        for f_opt in filter_options:
            current_ids = filter_result.get(str(f_opt[0]), set())
            current_ids.add(str(f_opt[1]))
            filter_result[str(f_opt[0])] = current_ids
        for key, val in filter_result.items():
            filter_result[key] = list(val)

        for fl_opt in filter_last_options:
            l_current_ids = filter_last_result.get(str(fl_opt[0]), set())
            l_current_ids.add(str(fl_opt[1]))
            filter_last_result[str(fl_opt[0])] = l_current_ids
        for k, v in filter_last_result.items():
            filter_last_result[k] = list(v)

        for fr in filter_value_range:
            filter_float_result[fr.get('attribute_id')] = [fr.get('min_value'), fr.get('max_value')]

        data['filter_options'] = json.dumps(filter_result)
        data['filter_float_options'] = json.dumps(filter_float_result)
        data['filter_last_options'] = json.dumps(filter_last_result)

        if category_change or page_load:
            in_filter_options = ProductAttributeValue.objects.values_list('attribute_id', 'value_option_id'). \
                filter(Q(product__categories__in=categories_ids),
                       Q(value_option_id__isnull=False))

            filter_result = self.get_filter_result(in_filter_options)

            filter_value_range = ProductAttributeValue.objects.values('attribute_id'). \
                annotate(min_value=Min('value_float'), max_value=Max('value_float')). \
                filter(Q(value_float__isnull=False),
                       Q(product__categories__in=categories_ids))

            filter_float_result = dict()
            for fr in filter_value_range:
                filter_float_result[fr.get('attribute_id')] = [fr.get('min_value'), fr.get('max_value')]

            options_data['filter_result'] = filter_result
            options_data['filter_float_result'] = filter_float_result

        data['products'] = products
        data['paginator'] = paginator
        data['page_size'] = page_size
        data['count_products'] = count_products
        data['all_variants'] = all_variants
        data['stock_yes'] = stock_yes
        data['unstock_yes'] = unstock_yes
        result = dict()

        options_data['category'] = category
        options_data['min_price'] = min_price
        options_data['max_price'] = max_price
        options_data['max_price_slider'] = max_price_slider

        html = render_to_string("catalogue/partials/product_ajax_filter.html", data, request=request)
        if category_change or page_load:
            html_options = render_to_string("catalogue/partials/options_ajax_filter.html", options_data,
                                            request=request)
            result['options_html'] = html_options

        result['html'] = html
        return HttpResponse(json.dumps(result), content_type='application/json')


class SalePages(SeoModuleCatalogueBrand, CommonFilterGetDataMixin, View):
    def __init__(self):
        self.template_page = 'catalogue/discounts_page.html'

    def get(self, request, *args, **kwargs):
        """Получение страницы - список товаров всех акций"""
        response = self.discounts_list(request)

        return response

    def discounts_list(self, request):
        """Обработчик для страницы с списком товаров всех акций"""
        # Берем все акции, действующие акции на данный момент времени
        now_date = timezone.now()
        current_discounts = Discount.objects.filter(start_datetime__lte=now_date,
                                                    end_datetime__gte=now_date)
        # Берем товары, которые участвуют в акциях
        current_discounts_products_ids = set()
        for current_discount in current_discounts:
            current_discounts_products_temp = current_discount.products.all()
            # Берем id товаров и избавляемся от дублирующихся товаров
            for prod in current_discounts_products_temp:
                current_discounts_products_ids.add(prod.id)

        # Берем только те товары, что есть в наличие
        current_discounts_products = Product.objects.filter(Q(id__in=current_discounts_products_ids),
                                                            Q(is_show=True),
                                                            Q(num_in_stock__gt=0),
                                                            Q(num_in_stock__gt=F('num_allocated')))
        # Берем максимальную и минимальную величину
        max_price = current_discounts_products.aggregate(Max('price_mrc')).get('price_mrc__max') or 0
        min_price = current_discounts_products.aggregate(Min('price_mrc'))['price_mrc__min'] or 0

        # Количество товаров, участвующих в акциях
        count_products = current_discounts_products.count()
        if current_discounts_products:
            pages = Paginator(current_discounts_products, 30)
            try:
                pages_content = pages.page(1)
            except PageNotAnInteger:
                pages_content = pages.page(1)
            except EmptyPage:
                pages_content = pages.page(pages.num_pages)
        else:
            pages_content = ''
            pages = ''

        # Значения аттрибутов для товаров, участвуют в фильтре
        filter_options = ProductAttributeValue.objects.values_list('attribute_id', 'value_option_id'). \
            filter(Q(product_id__in=current_discounts_products_ids),
                   Q(attribute__is_show=True)).order_by('attribute__display_order')

        filter_result = self.get_filter_result(filter_options)

        # Для страницы с акциями выводим основные аттрибуты в фильтре
        main_attributes = ProductAttribute.objects.filter(is_main=True)

        ctx = dict()
        ctx['discounts'] = current_discounts
        ctx['products'] = current_discounts_products
        ctx['count_products'] = count_products
        ctx['results'] = pages_content
        ctx['pages'] = pages
        ctx['min_price_slider'] = min_price
        ctx['max_price_slider'] = max_price
        ctx['min_price'] = min_price
        ctx['max_price'] = max_price
        ctx['main_attributes'] = main_attributes
        ctx['filter_result'] = filter_result

        response = render(request, self.template_page, ctx)
        response.set_cookie('current_prev', request.path)

        return response


def generate_sales_menu():
    """Генерация меню для товаров со скидками"""
    menu_categories_result = dict()
    ids = set()
    ids_parent = set()
    prod_category_ids = dict()
    prod_category_acc = dict()

    menu_categories = Category.objects.filter(level=2, name__in=['Коляски', 'Автокресла'])
    menu_categories_other = Category.objects.filter(level=3).exclude(parent__name__in=['Коляски', 'Автокресла'])

    # Берем все акции, действующие акции на данный момент времени
    now_date = timezone.now()
    current_discounts = Discount.objects.filter(start_datetime__lte=now_date,
                                                end_datetime__gte=now_date)
    # Берем товары, которые участвуют в акциях
    current_discounts_products_ids = set()
    for current_discount in current_discounts:
        current_discounts_products_temp = current_discount.products.all()
        # Берем id товаров и избавляемся от дублирующихся товаров
        for prod in current_discounts_products_temp:
            current_discounts_products_ids.add(prod.id)

    # Берем только те товары, что есть в наличие
    ids_all = Product.objects.values('categories__id', 'categories__parent', 'id', 'categories__name',
                                     'categories__parent__name', 'categories__slug'). \
        filter(Q(id__in=current_discounts_products_ids), Q(is_show=True),
               Q(num_in_stock__gt=0),
               Q(num_in_stock__gt=F('num_allocated')))

    # Перебираем родительские категории товаров (родитель и родитель родителя)
    for id in ids_all:
        ids.add(id['categories__parent'])
        ids.add(id['categories__id'])
        ids_parent.add(id['categories__parent'])
        if not id['categories__parent'] in prod_category_ids:
            prod_category_ids[id['categories__parent']] = []

        if not id['categories__parent__name'] in prod_category_acc:
            prod_category_acc[id['categories__parent__name']] = []

    menu_categories_main_ids = set()

    # Берем подкатегории для разделов Автокресла и Коляски
    for m in menu_categories:
        children_categories = m.get_children().filter(id__in=ids)
        # Если ни один подраздел не участвует в акции, то категория не отображается
        if children_categories:
            menu_categories_main_ids.add(m.pk)
            menu_categories_result[str(m.pk)] = children_categories

    # Берем подкатегории для разделов, отличных от Автокресла и Коляски
    for m in menu_categories_other:
        children_categories = m.get_children().filter(id__in=ids)
        # Если ни один подраздел не участвует в акции, то категория не отображается
        if children_categories:
            menu_categories_main_ids.add(m.pk)
            menu_categories_result[str(m.pk)] = children_categories

    # Получаем подкатегории по id
    menu_categories_main = Category.objects.filter(pk__in=menu_categories_main_ids)

    ctx = {
        'menu_categories': menu_categories_main,
        'menu_categories_result': menu_categories_result
    }
    # Ссылка на html, в который будет записываться готовое меню
    generate_html = os.path.join(settings.ROOT_DIR, 'templates/partials/promotions_categories_widget.html')
    # Отправляем данные в шаблон и получаем готовое меню
    content = render_to_string(settings.ROOT_DIR + '/common/templates/templatetags/promotions_category_widget.html',
                               ctx)
    content = html_minify(content)
    content = content.replace('<html><head></head><body>', '').replace('</body></html>', '')
    # Записываем в файл
    with open(generate_html, 'w') as static_file:
        static_file.write(content)
