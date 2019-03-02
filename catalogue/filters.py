from rest_framework_filters import (
    FilterSet, RelatedFilter,NumberFilter,
    AllLookupsFilter,)

from .models import (
    Category,
    Product,
)


class CategoryFilterSet(FilterSet):
    id = AllLookupsFilter()
    name = AllLookupsFilter()

    class Meta:
        model = Category


class ProductFilterSet(FilterSet):
    id = AllLookupsFilter()
    title = AllLookupsFilter()
    # categories = RelatedFilter(CategoryFilterSet)
    min_price = NumberFilter(name="price_mrc", lookup_expr='gte')
    max_price = NumberFilter(name="price_mrc", lookup_expr='lte')

    class Meta:
        model = Product
