from django.db.models import Q, F
from django.http import Http404
from rest_framework import renderers, status
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAdminUser
from catalogue.views import ProductCategoryView
from django.db.models import Count
from django.core.paginator import (Paginator, )

from address.models import UserAddress
from customer.filters import ChildrenFilterSet
from customer.models import Children
from customer.serializers import ChildrenSerializer, UserAddressSerializer

from catalogue.filters import ProductFilterSet
from catalogue.models import Product, ProductImage, Category, Brand
from catalogue.serializers import ProductSerializer, ProductImageSerializer, ProductDetailSerializer, \
    ProductDeliverySerialaizer, CityDeliverySerialaizer

from logistics_exchange.models import Office, City
from order.serializers import OfficeSerializer, CityOfficeSerializer
from order.filters import OfficeFilterSet, CityOfficeFilterSet

from common.serializers import CitySimpleSerializer
from common.filters import CitySimpleFilterSet

from discountmanager.serializers import CategoryAttributeSimilarSerializer, SelectionAttributeSerializer
from discountmanager.models import CategoryAttributeSimilar, SelectionAttribute

from .permissions import IsOwner, IsReadOnly


class ManyResultsSetPagination(PageNumberPagination):
    page_size = 5000
    page_size_query_param = 'page_size'
    max_page_size = 10000


class CityViewSet(ModelViewSet):
    queryset = City.objects.exclude(city_name='_root').order_by('city_name')
    serializer_class = CitySimpleSerializer
    filter_class = CitySimpleFilterSet
    pagination_class = ManyResultsSetPagination
    permission_classes = (IsReadOnly,)


class ChildrenViewSet(ModelViewSet):
    queryset = Children.objects.all()
    serializer_class = ChildrenSerializer
    filter_class = ChildrenFilterSet
    permission_classes = (IsOwner,)

    def get_queryset(self):
        user = self.request.user
        return Children.objects.filter(user=user)


class OfficeViewSet(ModelViewSet):
    queryset = Office.objects.all()
    serializer_class = OfficeSerializer
    filter_class = OfficeFilterSet
    permission_classes = (IsReadOnly,)


class CityOfficeViewSet(ModelViewSet):
    queryset = City.objects.all()
    serializer_class = CityOfficeSerializer
    filter_class = CityOfficeFilterSet
    permission_classes = (IsReadOnly,)


class UserAddressViewSet(ModelViewSet):
    queryset = UserAddress.objects.all()
    serializer_class = UserAddressSerializer
    permission_classes = (IsOwner,)

    def get_queryset(self):
        user = self.request.user
        return UserAddress.objects.filter(user=user)


class ProductImageViewSet(ModelViewSet):
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer
    permission_classes = (IsReadOnly,)


class ProductDeliveryViewSet(ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductDeliverySerialaizer
    permission_classes = (IsReadOnly,)


class CityDeliveryViewSet(ModelViewSet):
    queryset = City.objects.all()
    serializer_class = CityDeliverySerialaizer
    permission_classes = (IsReadOnly,)


class SelectionAttributeViewSet(ModelViewSet):
    queryset = SelectionAttribute.objects.all()
    serializer_class = SelectionAttributeSerializer
    permission_classes = (IsAdminUser,)


class CategoryAttributeSimilarViewSet(ModelViewSet):
    queryset = CategoryAttributeSimilar.objects.all()
    serializer_class = CategoryAttributeSimilarSerializer
    permission_classes = (IsAdminUser,)



class ProductViewSet(ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductDetailSerializer
    filter_class = ProductFilterSet
    permission_classes = (IsReadOnly,)

    def list(self, request, *args, **kwargs):
        print("List data")
        response = super().list(request, *args, **kwargs)

        min_price_data = self.filter_queryset(self.get_queryset()).order_by('price_mrc')
        min_price = 0
        if min_price_data:
            min_price = min_price_data[0].price_mrc
        response.data['min_price'] = min_price

        max_price_data = self.filter_queryset(self.get_queryset()).order_by('-price_mrc')
        max_price = 0
        if max_price_data:
            max_price = max_price_data[0].price_mrc
        response.data['max_price'] = max_price

        return response


class SmallResultsSetPagination(PageNumberPagination):
    page_size = 30
    page_size_query_param = 'page_size'
    max_page_size = 10000


class ProductCategoryViewSet(ModelViewSet):
    queryset = Product.objects.filter(price_mrc__gt=0)
    serializer_class = ProductSerializer
    filter_class = ProductFilterSet
    pagination_class = SmallResultsSetPagination
    renderer_classes = (renderers.TemplateHTMLRenderer,)

    def get_queryset(self):
        queryset = Product.objects.all()
        queryset = self.get_serializer_class().setup_eager_loading(queryset)
        search_param = self.request.query_params.get('operand', None)
        categories_raw = self.request.query_params.getlist('categories[]', None)
        sort = self.request.query_params.get('sort', None)
        search_phrase = self.request.query_params.get('search_phrase', None)
        categories_search = self.request.query_params.getlist('categories_search[]', None)
        brands = self.request.query_params.getlist('brands[]', None)
        if brands is not None and len(brands) > 0:
            brands_object = Brand.objects.filter(pk__in=brands)
        else:
            brands_object = None

        if search_param:
            if search_param == 'in':
                if search_phrase != '' and search_phrase is not None:
                    if categories_search:
                            if brands_object:
                                products_from_categories = Product.objects.filter((
                                                                Q(title__icontains='' + search_phrase + '')
                                                                | Q(artikul__icontains='' + search_phrase + '')),
                                                                Q(categories__in=categories_search),
                                                                Q(stockrecords__num_in_stock__gt=0),
                                                                Q(stockrecords__num_in_stock__gt=F('stockrecords__num_allocated')),
                                                                Q(brand__in=brands_object)).distinct()
                            else:
                                products_from_categories = Product.objects.filter((
                                                            Q(title__icontains='' + search_phrase + '') | Q(
                                                                artikul__icontains='' + search_phrase + '')),
                                                            Q(categories__in=categories_search),
                                                            Q(stockrecords__num_in_stock__gt=0),
                                                            Q(stockrecords__num_in_stock__gt=F('stockrecords__num_allocated')),
                                                            ).distinct()
                            if not products_from_categories:
                                products_from_categories = Product.objects.filter(
                                    Q(categories__in=categories_search),
                                    Q(stockrecords__num_in_stock__gt=0),
                                    Q(stockrecords__num_in_stock__gt=F('stockrecords__num_allocated')),
                                ).distinct()

                    else:
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

                        if brands_object:
                            products_from_categories = Product.objects.filter((Q(categories__in=categories_ids) | (
                                    Q(title__icontains='' + search_phrase + '') | Q(
                                        artikul__icontains='' + search_phrase + ''))),
                                    Q(stockrecords__num_in_stock__gt=0),
                                    Q(brand__in=brands_object),
                                    Q(stockrecords__num_in_stock__gt=F('stockrecords__num_allocated'))).distinct()
                        else:
                            products_from_categories = Product.objects.filter((Q(categories__in=categories_ids) | (
                                                    Q(title__icontains='' + search_phrase + '') | Q(
                                                                    artikul__icontains='' + search_phrase + ''))),
                                                    Q(stockrecords__num_in_stock__gt=0),
                                                    Q(stockrecords__num_in_stock__gt=F('stockrecords__num_allocated'))).distinct()

                    queryset = products_from_categories
                else:
                    category_access =[]
                    category_all = []
                    print('categories_raw======', categories_raw)
                    for cat in categories_raw:
                        category_id = Category.objects.get(id=cat)
                        if category_id.name.find("Аксессуары") != -1 or category_id.parent.name.find("Аксессуары") != -1:
                            category_access.append(cat)
                        else:
                            category_all.append(cat)

                    if len(category_access) > 0 and (sort is None or sort == '-' or sort == ''):
                        if brands_object:
                            queryset_access = queryset.filter(Q(categories__in=category_access), Q(price_mrc__gt=0),
                                                        Q(stockrecords__num_in_stock__gt=0),
                                                        Q(brand__in=brands_object),
                                                        Q(stockrecords__num_in_stock__gt=F('stockrecords__num_allocated'))).distinct()
                            queryset_all = queryset.filter(Q(categories__in=category_all), Q(price_mrc__gt=0),
                                                        Q(stockrecords__num_in_stock__gt=0),
                                                        Q(brand__in=brands_object),
                                                        Q(stockrecords__num_in_stock__gt=F('stockrecords__num_allocated'))).distinct()

                            queryset = queryset_all | queryset_access
                        else:
                            queryset_access = queryset.filter(Q(categories__in=category_access),
                                                                Q(price_mrc__gt=0),
                                                                Q(stockrecords__num_in_stock__gt=0),
                                                                Q(stockrecords__num_in_stock__gt=F('stockrecords__num_allocated'))).distinct().extra(select={'is_top': '0'})

                            queryset_all = queryset.filter(Q(categories__in=category_all),
                                                            Q(price_mrc__gt=0),
                                                            Q(stockrecords__num_in_stock__gt=0),
                                                            Q(stockrecords__num_in_stock__gt=F('stockrecords__num_allocated'))).distinct()
                            queryset = queryset_all | queryset_access
                            queryset = queryset.extra(order_by = ['is_top'])


                    else:
                        if brands_object:
                            queryset = queryset.filter(Q(categories__in=categories_raw), Q(price_mrc__gt=0),
                                                       Q(stockrecords__num_in_stock__gt=0),
                                                       Q(stockrecords__num_in_stock__gt=F('stockrecords__num_allocated')),
                                                       Q(brand__in=brands_object)).distinct()
                        else:
                            queryset = queryset.filter(Q(categories__in=categories_raw),
                                                       Q(price_mrc__gt=0),
                                                       Q(stockrecords__num_in_stock__gt=0),
                                                       Q(stockrecords__num_in_stock__gt=F('stockrecords__num_allocated'))).distinct()

                if sort is not None and sort != '-' and sort != '':
                    ordering_condition = ProductCategoryView.get_ordering_condition(self, '' + sort + '')
                    if ordering_condition == 'num_reviews' or ordering_condition == '-num_reviews':
                        queryset = queryset.annotate(
                                    num_reviews=Count('reviews')).order_by(ordering_condition).distinct()
                    else:
                        queryset = queryset.order_by(ordering_condition).distinct()
                else:
                    queryset = queryset.order_by('-date_created')
        return queryset

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)

        min_price = self.request.query_params.get('min_price', None)
        if min_price is None:
            min_price_data = self.filter_queryset(self.get_queryset()).order_by('price_mrc')
            min_price = 0
            if min_price_data:
                min_price = min_price_data[0].price_mrc
            response.data['min_price'] = min_price

        max_price = self.request.query_params.get('max_price', None)
        if max_price is None:
            max_price_data = self.filter_queryset(self.get_queryset()).order_by('-price_mrc')
            max_price = 0
            if max_price_data:
                max_price = max_price_data[0].price_mrc
            response.data['max_price'] = max_price

        categories_raw = self.request.query_params.get('categories_data', None)
        response.data['categories_raw'] = categories_raw

        categories_arr = self.request.query_params.getlist('categories[]', None)

        current_page = self.request.query_params.get('page', None)
        response.data['page'] = current_page

        class_button = self.request.query_params.get('class_button', None)
        response.data['class_button'] = class_button

        search_phrase = self.request.query_params.get('search_phrase', None)
        brands = self.request.query_params.getlist('brands[]', None)
        if search_phrase != '' and search_phrase is not None:
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
            products_from_categories = Product.objects.filter((Q(categories__in=categories_ids) | (
                Q(title__icontains='' + search_phrase + '') | Q(artikul__icontains='' + search_phrase + ''))),
                                                              Q(price_mrc__gte=min_price),
                                                              Q(price_mrc__lte=max_price),
                                                              Q(stockrecords__num_in_stock__gt=0),
                                                              Q(stockrecords__num_in_stock__gt=F('stockrecords__num_allocated'))).order_by(
                'price_mrc').distinct()

            paginator_query = products_from_categories
        else:
            paginator_query = Product.objects.filter(Q(categories__in=categories_arr), Q(price_mrc__gt=0),
                                                            Q(stockrecords__num_in_stock__gt=0),
                                                            Q(stockrecords__num_in_stock__gt=F('stockrecords__num_allocated')),
                                                            Q(price_mrc__gte=min_price),
                                                            Q(price_mrc__lte=max_price)).distinct()

        if brands:
            paginator_query = paginator_query.filter(brand__in=brands)

        p = Paginator(paginator_query, self.request.query_params.get('page_size', None))
        response.data['paginator'] = p

        mode = self.request.query_params.get('mode', None)
        verify_cats_temp = self.request.query_params.getlist('verify_cats[]', None)
        verify_brands_temp = self.request.query_params.getlist('verify_brands[]', None)
        checked_cats = self.request.query_params.getlist('checked_cats[]', None)
        checked_brands = self.request.query_params.getlist('checked_brands[]', None)
        verify_brands = [value for value in verify_brands_temp if value]
        verify_cats = [value for value in verify_cats_temp if value]

        ids_gray = self.verify_cats_and_brands(verify_cats, verify_brands, min_price, max_price, mode, checked_cats, checked_brands)
        response.data['ids_gray_cats'] = ids_gray['ids_gray_cats']
        response.data['ids_gray_brands'] = ids_gray['ids_gray_brands']

        if request.accepted_renderer.format == 'html':
            return Response({'data': response.data}, template_name='products_filter.html')
        return response
