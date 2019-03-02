from django.conf import urls

from .views import (
    BasketView,
    BasketAddView,
    RemoveBasketLine,
    register_customer_from_basket,
    AddPvzAptAjax,
    ChangeQuantity,
    get_courier_delivery_date,
    check_stocks_for_basket,
    SpsrDataView,
    SpsrCourierDeliveryView,
    SpsrCallCentrDeliveryView,
)

app_name = 'basket'

urlpatterns = [
    urls.url(r'^$', BasketView.as_view(), name='summary'),
    urls.url(r'spsr_delivery_data/$', SpsrDataView.as_view(), name='get_spsr_delivery_data'),
    urls.url(r'spsr_courier_delivery_data/$', get_courier_delivery_date, name='get_courier_delivery_date'),
    urls.url(r'spsr_delivery_call/$', SpsrCallCentrDeliveryView.as_view(), name='get_spsr_delivery_call_centr'),
    urls.url(r'check_stocks_for_basket/$', check_stocks_for_basket, name='check_stocks_for_basket'),
    urls.url(r'^add/(?P<pk>\d+)/$', BasketAddView.as_view(), name='add'),
    urls.url(r'^remove/(?P<pk>\d+)/$', RemoveBasketLine.as_view(), name='remove'),
    urls.url(r'^pvz_apt/', AddPvzAptAjax.as_view(), name='remove'),
    urls.url(r'^registration-from-basket/', register_customer_from_basket, name='registration-from-basket'),
    urls.url(r'^changequantity/(?P<pk>\d+)/$', ChangeQuantity.as_view(), name='change_quantity'),
    urls.url(r'^spsrcourier/$', SpsrCourierDeliveryView.as_view(), name='spsr_courier'),
    urls.url(r'^spsrdata/$', SpsrDataView.as_view(), name='data_spsr'),

]
