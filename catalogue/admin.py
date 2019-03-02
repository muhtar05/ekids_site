from django.contrib import admin
from mptt.admin import MPTTModelAdmin
from django_mptt_admin.admin import DjangoMpttAdmin

from .models import (
    Category, Product,
    MenuCategory, ProductImage,
    ProductRecommendation, ProductClass,
    ProductCategory, ProductAttribute,
    ProductAttributeValue,
    ProductAttributeOptionGroup, ProductAttributeOption,
    ProductGift, Brand, FilterItem, ContractorCatalogue,
    ProductAttributeCategory,
)


class AttributeInline(admin.TabularInline):
    model = ProductAttributeValue


class ProductRecommendationInline(admin.TabularInline):
    model = ProductRecommendation
    fk_name = 'primary'
    raw_id_fields = ['primary', 'recommendation']


class CategoryInline(admin.TabularInline):
    model = ProductCategory
    extra = 1


class ProductAttributeInline(admin.TabularInline):
    model = ProductAttribute
    extra = 2


class ProductClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'requires_shipping', 'track_stock')
    prepopulated_fields = {"slug": ("name",)}
    # inlines = [ProductAttributeInline]


class BrandAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ('name',)

    class Media:
        js = (
            '/static/tiny_mce/tiny_mce.js',
            '/static/tiny_mce/tiny_mce_init.js',
        )


class FilterItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'show', 'position')
    list_filter = ['show']


class ProductAdmin(admin.ModelAdmin):
    date_hierarchy = 'date_created'
    list_display = ('get_title', 'get_product_class', 'item_id', 'structure',
                    'attribute_summary', 'date_created', 'product_contractor')
    list_filter = ['structure', 'is_discountable']
    raw_id_fields = ['parent']
    # readonly_fields = ('')
    # inlines = [AttributeInline, CategoryInline, ProductRecommendationInline]
    # prepopulated_fields = {"slug": ("title",)}
    search_fields = ['upc', 'title']

    def get_queryset(self, request):
        qs = super(ProductAdmin, self).get_queryset(request)
        return (
            qs
            .select_related('product_class', 'parent')
            .prefetch_related(
                'attribute_values',
                'attribute_values__attribute'))


class ProductAttributeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'type')
    prepopulated_fields = {"code": ("name", )}


class ProductAttributeCategoryAdmin(admin.ModelAdmin):
    list_display = ('category', 'attribute', )
    list_filter = ('category', 'attribute')


class ProductAttributeValueAdmin(admin.ModelAdmin):
    list_display = ('product', 'attribute', 'value')
    list_filter = ('attribute',)


class AttributeOptionInline(admin.TabularInline):
    model = ProductAttributeOption


class ProductAttributeOptionGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'option_summary')
    inlines = [AttributeOptionInline]


class ProductAttributeOptionAdmin(admin.ModelAdmin):
    list_display = ('option','show_value','id_attribute_option', 'get_group_name','color_code')
    list_filter = ('group',)

    def get_group_name(self, object):
        return object.group.name


class CategoryAdmin(DjangoMpttAdmin):
    readonly_fields = ('pk', 'lft', 'rght', 'tree_id', 'level')
    list_display = ('name', 'id_category')
    # prepopulated_fields = {'slug': ('name',)}

    class Media:
        js = (
            '/static/tiny_mce/tiny_mce.js',
            '/static/tiny_mce/tiny_mce_init.js',
        )

admin.site.register(ProductClass, ProductClassAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(ProductAttribute, ProductAttributeAdmin)
admin.site.register(ProductAttributeCategory, ProductAttributeCategoryAdmin)
admin.site.register(ProductAttributeValue, ProductAttributeValueAdmin)
admin.site.register(ProductAttributeOptionGroup, ProductAttributeOptionGroupAdmin)
admin.site.register(ProductImage)
admin.site.register(Category, CategoryAdmin)
admin.site.register(ProductCategory)
admin.site.register(MenuCategory)
admin.site.register(ProductGift)
admin.site.register(Brand, BrandAdmin)
admin.site.register(FilterItem, FilterItemAdmin)
admin.site.register(ContractorCatalogue)
admin.site.register(ProductAttributeOption, ProductAttributeOptionAdmin)
