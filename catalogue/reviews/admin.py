from django.contrib import admin
from mptt.admin import MPTTModelAdmin

from .models import ProductReview, Vote, ReviewComment


class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ('product',  'workmanship_score', 'status', 'total_votes',
                    'delta_votes', 'date_created')
    readonly_fields = ('total_votes', 'delta_votes')


class ReviewCommentAdmin(MPTTModelAdmin):
    readonly_fields = ('pk', 'lft', 'rght', 'tree_id', 'level')


class VoteAdmin(admin.ModelAdmin):
    list_display = ('review', 'user', 'delta', 'date_created')


admin.site.register(ProductReview, ProductReviewAdmin)
admin.site.register(Vote, VoteAdmin)
admin.site.register(ReviewComment, ReviewCommentAdmin)
