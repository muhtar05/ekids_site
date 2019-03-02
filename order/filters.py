from rest_framework_filters import (
    FilterSet, RelatedFilter,NumberFilter,
    AllLookupsFilter,)

from logistics_exchange.models import Office, City


class OfficeFilterSet(FilterSet):
    city_name = AllLookupsFilter()

    class Meta:
        model = Office


class CityOfficeFilterSet(FilterSet):
    city_name = AllLookupsFilter()

    class Meta:
        model = City

#
# class ProductFilterSet(FilterSet):
#     id = AllLookupsFilter()
#     title = AllLookupsFilter()
#     # categories = RelatedFilter(CategoryFilterSet)
#     min_price = NumberFilter(name="price_mrc", lookup_expr='gte')
#     max_price = NumberFilter(name="price_mrc", lookup_expr='lte')
#
#     class Meta:
#         model = Product
