from django.contrib import admin

from basket.models import (Basket, Line, DeliveryBasket,
                           LineAttribute, StockReserve, BasketHistoryReserve,OldReserveLine,)


class LineInline(admin.TabularInline):
    model = Line
    readonly_fields = ('line_reference', 'product', 'price_excl_tax',
                       'price_incl_tax', 'price_currency', 'stockrecord')


class LineAdmin(admin.ModelAdmin):
    list_display = ('id', 'basket', 'product', 'stockrecord', 'quantity',
                    'price_excl_tax', 'price_currency', 'date_created')
    readonly_fields = ('basket', 'stockrecord', 'line_reference', 'product',
                       'price_currency', 'price_incl_tax', 'price_excl_tax',
                       'quantity')


class BasketAdmin(admin.ModelAdmin):
    list_display = ('id', 'owner', 'status', 'num_lines',
                    'date_created', 'date_submitted',
                    'time_before_submit')
    readonly_fields = ('owner', 'date_merged', 'date_submitted')
    inlines = [LineInline]


class LineReserveTimeAdmin(admin.ModelAdmin):
    list_display = ('basket', 'line', 'created_at', 'quantity')


class StockReserveAdmin(admin.ModelAdmin):
    list_display = ('line', 'start_reserve', 'end_reserve','is_active')
    readonly_fields = ('line',)


class BasketHistoryReserveAdmin(admin.ModelAdmin):
    list_display = ('basket','start_time','end_time', 'position')


admin.site.register(Basket, BasketAdmin)
admin.site.register(Line, LineAdmin)
admin.site.register(LineAttribute)
admin.site.register(DeliveryBasket)
admin.site.register(StockReserve, StockReserveAdmin)
admin.site.register(BasketHistoryReserve, BasketHistoryReserveAdmin)
admin.site.register(OldReserveLine)