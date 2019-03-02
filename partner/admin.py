from django.contrib import admin

from .models import Partner, StockRecord


class StockRecordAdmin(admin.ModelAdmin):
    list_display = ('get_product_pk', 'date_updated', 'price_excl_tax',
                    'num_in_stock', 'num_allocated',)
    list_filter = ('partner', 'num_in_stock', 'num_allocated', 'date_updated')
    search_fields = ('product__artikul',)

    def get_product_pk(self, obj):
        return obj.product.pk

    get_product_pk.short_description = 'Product'
    get_product_pk.admin_order_field = 'product'

admin.site.register(Partner)
admin.site.register(StockRecord, StockRecordAdmin)
