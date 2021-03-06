import json
from django.http import HttpResponse
from django.conf import settings
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import ugettext_lazy as _
from django.views.generic import CreateView, DetailView, ListView, View

from catalogue.reviews.signals import review_added
from core.loading import get_classes, get_model
from core.utils import redirect_to_referrer

from catalogue.reviews.forms import (ProductReviewForm, VoteForm,
                                     SortReviewsForm, ReviewCommentForm,
                                     )

from catalogue.reviews.models import Vote, ProductReview, ReviewComment
from catalogue.models import Product


class CreateProductReview(CreateView):
    http_method_names = ['post']
    model = ProductReview
    product_model = Product
    form_class = ProductReviewForm

    def dispatch(self, request, *args, **kwargs):
        self.product = get_object_or_404(
            self.product_model, pk=kwargs['product_pk'])
        if not self.product.is_review_permitted(request.user):
            if self.product.has_review_by(request.user):
                message = _("Вы уже оставляли отзыв на данный продукт")
            else:
                message = _("Вы не можете оставить отзыв на данный продукт")
            messages.warning(self.request, message)
            return redirect(self.product.get_absolute_url())
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['product'] = self.product
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        # self.send_signal(self.request, response, self.object)
        return response

    def form_invalid(self, form):
        response = super().form_invalid(form)
        return response

    def get_success_url(self):
        messages.success(
            self.request, _("Спасибо, что оставили отзыв о данном товаре"))
        return self.product.get_absolute_url()


class ProductReviewDetail(DetailView):
    template_name = "catalogue/reviews/review_detail.html"
    context_object_name = 'review'
    model = ProductReview

    def get_context_data(self, **kwargs):
        context = super(ProductReviewDetail, self).get_context_data(**kwargs)
        context['product'] = get_object_or_404(
            Product, pk=self.kwargs['product_pk'])
        return context


class AddVoteView(View):
    """
    Simple view for voting on a review.

    We use the URL path to determine the product and review and use a 'delta'
    POST variable to indicate it the vote is up or down.
    """

    def post(self, request, *args, **kwargs):
        product = get_object_or_404(Product, pk=self.kwargs['product_pk'])
        review = get_object_or_404(ProductReview, pk=self.kwargs['pk'])

        form = VoteForm(review, request.user, request.POST)
        if form.is_valid():
            if form.is_up_vote:
                review.vote_up(request.user)
            elif form.is_down_vote:
                review.vote_down(request.user)
            messages.success(request, _("Thanks for voting!"))
        else:
            for error_list in form.errors.values():
                for msg in error_list:
                    messages.error(request, msg)
        return redirect_to_referrer(request, product.get_absolute_url())


class ProductReviewList(ListView):
    """
    Browse reviews for a product
    """
    template_name = 'catalogue/reviews/review_list.html'
    context_object_name = "reviews"
    model = ProductReview
    product_model = Product
    paginate_by = 5

    def get_queryset(self):
        qs = self.model.objects.approved().filter(product=self.kwargs['product_pk'])
        self.form = SortReviewsForm(self.request.GET)
        if self.form.is_valid():
            sort_by = self.form.cleaned_data['sort_by']
            if sort_by == SortReviewsForm.SORT_BY_RECENCY:
                return qs.order_by('-date_created')
        return qs.order_by('-workmanship_score ')

    def get_context_data(self, **kwargs):
        context = super(ProductReviewList, self).get_context_data(**kwargs)
        context['product'] = get_object_or_404(
            self.product_model, pk=self.kwargs['product_pk'])
        context['form'] = self.form
        return context


def add_comment(request, product_pk, product_slug):
    if request.is_ajax():
        form = ReviewCommentForm(request.POST)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.user = request.user
            instance.save()
            data = {
                'status': 'ok',
                'review_body': instance.body,
                'review_user': instance.reviewer_name,
                'review_date': instance.date_created.strftime('%d %B %Y г. %H:%M'),
            }
        else:
            data = {'status': 'error', 'errors': form.errors}
        return HttpResponse(json.dumps(data), content_type='application/json')
