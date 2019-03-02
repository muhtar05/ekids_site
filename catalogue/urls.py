from django.conf import urls
from django.conf.urls import include

from .views import (
    ProductDetailView,
    ProductCategoryView,
    get_filter_data,
    ProductCategoryAjaxView,
)


app_name = 'catalogue'


urlpatterns = [
    urls.url(r'^catalogue/product_ajax_category/$', ProductCategoryAjaxView.as_view(), name='product_ajax_category'),
    urls.url(r'^product/(?P<product_slug>[\w-]*)_(?P<pk>\d+)/$', ProductDetailView.as_view(), name='detail'),
    urls.url(r'^catalogue/(?P<category_slug>[\w-]+(/[\w-]+)*)/$', ProductCategoryView.as_view(), name='category'),
    urls.url(r'^catalogue/(?P<seofilter_page>[\w-]+(/[\w-]+)*)/$',ProductCategoryView.as_view(), name='category'),
    urls.url(r'^(?P<product_slug>[\w-]*)_(?P<product_pk>\d+)/reviews/',
                include('catalogue.reviews.urls')),
    urls.url(r'^catalogue/filter_data', get_filter_data, name='filter-data'),

]
