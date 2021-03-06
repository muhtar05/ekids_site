from django import forms
from django.utils.translation import ugettext_lazy as _

from .models import ProductReview, Vote, ReviewComment


class ProductReviewForm(forms.ModelForm):
    name = forms.CharField(label=_('Name'), required=True)
    email = forms.EmailField(label=_('Email'), required=False)

    def __init__(self, product, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.product = product
        if user and user.is_authenticated():
            self.instance.user = user
            del self.fields['name']
            del self.fields['email']

    class Meta:
        model = ProductReview
        fields = ('workmanship_score',
                  'service_ability_score', 'body',
                  'name', 'email', 'impression',
                  'dignity', 'limitations', 'age_child',
        )


class VoteForm(forms.ModelForm):

    class Meta:
        model = Vote
        fields = ('delta',)

    def __init__(self, review, user, *args, **kwargs):
        super(VoteForm, self).__init__(*args, **kwargs)
        self.instance.review = review
        self.instance.user = user

    @property
    def is_up_vote(self):
        return self.cleaned_data['delta'] == Vote.UP

    @property
    def is_down_vote(self):
        return self.cleaned_data['delta'] == Vote.DOWN


class SortReviewsForm(forms.Form):
    SORT_BY_SCORE = 'score'
    SORT_BY_RECENCY = 'recency'
    SORT_REVIEWS_BY_CHOICES = (
        (SORT_BY_SCORE, _('Score')),
        (SORT_BY_RECENCY, _('Recency')),
    )

    sort_by = forms.ChoiceField(
        choices=SORT_REVIEWS_BY_CHOICES,
        label=_('Sort by'),
        initial=SORT_BY_SCORE,
    )


class ReviewCommentForm(forms.ModelForm):

    class Meta:
        model = ReviewComment
        fields = ('body','review',)
