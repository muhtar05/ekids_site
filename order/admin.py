from django.contrib import admin

from order.models import (Order, OrderNote, CommunicationEvent,
                          ShippingAddress, Line, LinePrice,
                          ShippingEvent, ShippingEventType, PaymentEvent,
                          PaymentEventType, PaymentEventQuantity, LineAttribute,
                          OrderDiscount, BillingAddress,
                          ShipmentMethod, PaymentStatus,
                          ShipmentStatus, OrderStatus, StatusGroup,
                          PaymentType, RecallReason, CancelReason,
                          ChangeLine,DoubleProductLine,
                          )


class LineInline(admin.TabularInline):
    model = Line
    extra = 0


class OrderAdmin(admin.ModelAdmin):
    raw_id_fields = ['user', 'billing_address', 'shipping_address', ]
    list_display = ('number', 'total_incl_tax', 'payment_type', 'user', 'status',
                    'post_id', 'post_id_pick', 'date_placed','recall_time')
    readonly_fields = ('number', 'total_incl_tax', 'total_excl_tax',
                       'shipping_incl_tax', 'shipping_excl_tax','basket')
    # inlines = [LineInline]


class LineAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'stockrecord', 'quantity')
    readonly_fields = ('product','stockrecord',)

class ChangeLineAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'stockrecord', 'quantity')


class LinePriceAdmin(admin.ModelAdmin):
    list_display = ('order', 'line', 'price_incl_tax', 'quantity')


class ShippingEventTypeAdmin(admin.ModelAdmin):
    list_display = ('name',)


class PaymentEventQuantityInline(admin.TabularInline):
    model = PaymentEventQuantity
    extra = 0


class PaymentEventAdmin(admin.ModelAdmin):
    list_display = ('order', 'event_type', 'amount', 'num_affected_lines',
                    'date_created')
    inlines = [PaymentEventQuantityInline]


class PaymentEventTypeAdmin(admin.ModelAdmin):
    pass


class OrderDiscountAdmin(admin.ModelAdmin):
    readonly_fields = ('order', 'category', 'offer_id', 'offer_name',
                       'voucher_id', 'voucher_code', 'amount')
    list_display = ('order', 'category', 'offer', 'voucher',
                    'voucher_code', 'amount')


class OrderStatusAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'display_name', 'group')
    ordering = ('id',)


class StatusGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'display_name', 'status_class')
    ordering = ('id',)


class RecallReasonAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')
    ordering = ('id',)

admin.site.register(Order, OrderAdmin)
# admin.site.register(Order)
# admin.site.register(OrderNote)
admin.site.register(ShippingAddress)
admin.site.register(Line, LineAdmin)
admin.site.register(ChangeLine, ChangeLineAdmin)
# admin.site.register(LinePrice, LinePriceAdmin)
# admin.site.register(ShippingEvent)
# admin.site.register(ShippingEventType, ShippingEventTypeAdmin)
admin.site.register(PaymentEvent, PaymentEventAdmin)
admin.site.register(PaymentEventType, PaymentEventTypeAdmin)
admin.site.register(LineAttribute)
# admin.site.register(OrderDiscount, OrderDiscountAdmin)
# admin.site.register(CommunicationEvent)
admin.site.register(ShipmentMethod)
admin.site.register(PaymentStatus)
# admin.site.register(ShipmentStatus)
admin.site.register(OrderStatus, OrderStatusAdmin)
admin.site.register(StatusGroup, StatusGroupAdmin)
admin.site.register(PaymentType)
admin.site.register(RecallReason, RecallReasonAdmin)
admin.site.register(CancelReason)
admin.site.register(DoubleProductLine)
