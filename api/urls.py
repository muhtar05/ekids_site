from rest_framework import routers

from .views import (
   ChildrenViewSet,
   ProductViewSet,
   ProductImageViewSet,
   UserAddressViewSet,
   ProductDeliveryViewSet,
   OfficeViewSet,
   CityOfficeViewSet,
   CityViewSet,
   CityDeliveryViewSet,
   CategoryAttributeSimilarViewSet,
   SelectionAttributeViewSet,
)


router = routers.DefaultRouter()


router.register(r'children', ChildrenViewSet)
router.register(r'products', ProductViewSet)
router.register(r'office', OfficeViewSet)
router.register(r'locations', CityViewSet)
router.register(r'cityoffice', CityOfficeViewSet)
router.register(r'productimages', ProductImageViewSet)
router.register(r'useraddress', UserAddressViewSet)
router.register(r'delivery', ProductDeliveryViewSet, base_name='products_delivery')
router.register(r'city_delivery', CityDeliveryViewSet, base_name='city_delivery')
router.register(r'similar_attributes', CategoryAttributeSimilarViewSet, base_name='similar_attributes')
router.register(r'selection_attributes', SelectionAttributeViewSet, base_name='selection_attributes')


urlpatterns = router.urls
