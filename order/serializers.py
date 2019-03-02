from rest_framework import serializers
from rest_framework.serializers import (
    ModelSerializer, ImageField,
    FileField, PrimaryKeyRelatedField,
)

from logistics_exchange.models import City, Office, OfficePhone


class CityOfficeSerializer(ModelSerializer):
    class Meta:
        model = City

        fields = (
            'id',
            'city_name',
            'city_id',
            'region_name',
            'city_owner_id',
            'dep_owner_id',
        )


class OfficeSerializer(ModelSerializer):

    class Meta:
        model = Office

        fields = (
            'pk',
            'unified_number',
            'office_id',
            'office_owner_id',
            'office_pt_name',
            'address',
            'subway',
            'work_time',
            'type_title',
            'city_name',
        )


# class ProductSerializer(ModelSerializer):
#     categories = CategorySerializer(many=True, read_only=True)
#     images = ProductImageSerializer(many=True, read_only=True)
#     main_img = serializers.SerializerMethodField()
#     price_mrc = serializers.SerializerMethodField()
#     prod = serializers.SerializerMethodField()
#     variants = serializers.SerializerMethodField()
#     discount_product = ProductSalesSerializer(many=True, read_only=True)
#
#     class Meta:
#         model = Product
#
#         fields = (
#             'id',
#             'title',
#             'slug',
#             'product_1c_id',
#             'price_mrc',
#             'categories',
#             'images',
#             'main_img',
#             'prod',
#             'variants',
#             'discount_product'
#
#         )
#
#     def get_main_img(self, obj):
#         img = obj.primary_image()
#         return img
#
#     def get_prod(self, obj):
#         return obj
#
#     def get_price_mrc(self, obj):
#         price_mrc = int(obj.price_mrc)
#         return price_mrc
#
#     def get_variants(self, obj):
#         return Product.objects.prefetch_related('images').filter(item_id=obj.item_id).exclude(item_id=0)[:6]
#
#     @staticmethod
#     def setup_eager_loading(queryset):
#         # # "one: relationships
#         # queryset = queryset.select_related('contractor', 'internal', 'internal__head_user', )
#         # # "to-many" relationships
#         queryset = queryset.prefetch_related('categories', 'images','stockrecords')
#         return queryset
