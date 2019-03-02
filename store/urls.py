from filebrowser.sites import site
"""store URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls import url, include
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import index
from django.contrib.sitemaps.views import sitemap
from catalogue.views import BrandList, BrandPage
from django.views.decorators.cache import cache_page

import debug_toolbar

from common.views import (CustomRegistrationView, Sertificaty, ForgotPasswordView,
                          MainSitemap, FloatPageSitemap,
                          )
from catalogue.views import (BrandsSitemap, CategoriesSitemap, ProductsSitemap,
                             SeoFilterSitemap, SearchPageView,)
from robots import views as rob_views
from market_yandex_google.utils import show_feed_yandex, show_feed_google, show_feed_facebook
from catalogue.views import SalePages
from . import views

sitemaps = {
    'main': MainSitemap,
    'catalog': CategoriesSitemap,
    'products': ProductsSitemap,
    'filterpage': SeoFilterSitemap,
    'floatpage': FloatPageSitemap,
    'brands': BrandsSitemap,
}

urlpatterns = [
    url(r'^$', views.home, name='home'),
    url(r'^hometest/$', views.home_test, name='home-test'),
    url(r'^dostavka/$', include('django.contrib.flatpages.urls')),
    url(r'^', include('catalogue.urls')),
    url(r'^getip/$', views.get_client_ip, name='getip'),
    # url(r'^testmail/$', views.test_mail, name='testmail'),
    # url(r'^parsers/', include('parsers.urls')),
    url(r'^payment/', include('payment.urls')),
    url(r'search/$', SearchPageView.as_view(), name='searchs'),
    url(r'^common/', include('common.urls')),
    url(r'^basket/', include('basket.urls')),
    url(r'^checkout/', include('checkout.urls')),
    url(r'^i18n/', include('django.conf.urls.i18n')),
    url(r'^accounts/register/$', CustomRegistrationView.as_view(), name='registration_register'),
    url(r'^accounts/forgot_password/$', ForgotPasswordView.as_view(), name='forgot_password'),
    url(r'^accounts/', include('registration.backends.default.urls')),
    url(r'^accounts/', include('password_reset.urls')),
    url(r'^accounts/', include('customer.urls')),
    url(r'^chadoadmin/', admin.site.urls),
    # url(r'^news/', include('news.urls')),
    url(r'^brand/$', BrandList.as_view(), name='brand_list'),
    url(r'^sertifikaty/$', Sertificaty.as_view(), name='sertifikaty'),
    url(r'^brand/(?P<slug>[\w-]*)/$', BrandPage.as_view(), name='brand_page'),
    url(r'^wishlist/', include('wishlists.urls')),
    url(r'^callcentr/', include('call_centr.urls')),
    url(r'^comparelist/', include('comparelists.urls')),
    url(r'^chadoapi/', include('api.urls')),
    url(r'^chado_yml\.yml$', show_feed_yandex, name='show_feed_yandex'),
    url(r'^chado_xml\.xml$', show_feed_google, name='show_feed_google'),
    url(r'^chado_fb_xml\.xml$', show_feed_facebook, name='show_feed_facebook'),
    url(r'^robots\.txt$', rob_views.create, name='create'),
    url(r'^o-kompanii/', include('django.contrib.flatpages.urls')),
    url(r'^tinymce/', include('tinymce.urls')),
    url(r'^ordermanagerwallet/', include('ordermanagerwallet.urls')),
    url(r'^discountmanager/', include('discountmanager.urls')),
    url(r'^promotions/', SalePages.as_view(), name='sales_page'),
    url(r'^exchange_to_site/', include('exchange_to_site.urls')),
    url(r'^seo/', include('seo.urls')),
    url(r'^sitemap.xml$', cache_page(86400)(index), {'sitemaps': sitemaps}),
    url(r'^sitemap-(?P<section>.+).xml$', cache_page(86400)(sitemap), {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    url(r'^articles/', include('articles.urls')),
    url(r'^ckeditor/', include('ckeditor_uploader.urls')),
    url(r'^driver_workplace/', include('driver_workplace.urls')),

    url(r'^__debug__/', include(debug_toolbar.urls)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
