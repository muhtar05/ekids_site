from django.conf import urls

from .views import (
    ProductReviewDetail,
    CreateProductReview,
    AddVoteView,
    ProductReviewList,
    add_comment,
)


urlpatterns = [
    urls.url(r'^(?P<pk>\d+)/$', ProductReviewDetail.as_view(), name='reviews-detail'),
    urls.url(r'^add/$', CreateProductReview.as_view(), name='reviews-add'),
    urls.url(r'^addcomment/$', add_comment, name='add-comment'),
    urls.url(r'^(?P<pk>\d+)/vote/$', AddVoteView.as_view(), name='reviews-vote'),
    urls.url(r'^$', ProductReviewList.as_view(), name='reviews-list'),
]
