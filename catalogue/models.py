import logging
import os
import math
from datetime import date, datetime

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.staticfiles.finders import find
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.files.base import File
from django.core.urlresolvers import reverse
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Count, Sum, Q, F, Max
from django.utils import six, timezone
from django.utils.functional import cached_property
from django.utils.html import strip_tags
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import get_language, pgettext_lazy

from mptt.models import TreeForeignKey, MPTTModel

from core.loading import get_class, get_classes, get_model
from core.utils import slugify
from core.validators import non_python_keyword
from core_models.fields import AutoSlugField, NullCharField
from core_models.fields.slugfield import SlugField

from .managers import ProductManager, BrowsableProductManager
from .product_attributes import ProductAttributesContainer
from logistics_exchange.models import City as Spsr_city
from exchange_to_site.models import Good

# Selector = get_class('partner.strategy', 'Selector')


class ProductClass(models.Model):
    """
    Used for defining options and attributes for a subset of products.
    E.g. Books, DVDs and Toys. A product can only belong to one product class.

    At least one product class must be created when setting up a new
    Oscar deployment.

    Not necessarily equivalent to top-level categories but usually will be.
    """
    name = models.CharField(_('Name'), max_length=128)
    slug = models.SlugField(_('Slug'), max_length=128, unique=True)

    #: Some product type don't require shipping (eg digital products) - we use
    #: this field to take some shortcuts in the checkout.
    requires_shipping = models.BooleanField(_("Requires shipping?"),
                                            default=True)

    #: Digital products generally don't require their stock levels to be
    #: tracked.
    track_stock = models.BooleanField(_("Track stock levels?"), default=True)

    #: These are the options (set by the user when they add to basket) for this
    #: item class.  For instance, a product class of "SMS message" would always
    #: require a message to be specified before it could be bought.
    #: Note that you can also set options on a per-product level.
    options = models.ManyToManyField(
        'catalogue.Option', blank=True, verbose_name=_("Options"))

    class Meta:
        app_label = 'catalogue'
        ordering = ['name']
        verbose_name = 'Продукты класса'
        verbose_name_plural = 'Продукты класса'

    def __str__(self):
        return self.name

    @property
    def has_attributes(self):
        return self.attributes.exists()


class Category(MPTTModel):
    name = models.CharField(_('Name'), max_length=255, db_index=True)
    description = models.TextField(_('Description'), blank=True)
    top_icon_name = models.CharField(max_length=100, null=True, blank=True)
    icon_name = models.CharField(max_length=100, null=True, blank=True)
    image = models.ImageField(_('Image'), upload_to='categories', blank=True,
                              null=True, max_length=255)
    id_category = models.CharField(max_length=20)
    position = models.IntegerField(default=0)
    slug = SlugField(_('Slug'), max_length=255, db_index=True)
    parent = TreeForeignKey('self', blank=True, null=True,
                            related_name='children', db_index=True)

    name_i = models.CharField(_('Название в именительном падеже'), max_length=255, db_index=True, null=True)
    name_r = models.CharField(_('Название в родительном падеже'), max_length=255, db_index=True, null=True)
    name_v = models.CharField(_('Название в винительном падеже'), max_length=255, db_index=True, null=True)
    name_p = models.CharField(_('Название в предложном падеже'), max_length=255, db_index=True, null=True)
    name_plural = models.CharField(_('Название во множественном числе'), max_length=255, db_index=True, null=True)
    name_plural_r = models.CharField(_('Название во множественном числе в род. падеже'), max_length=255, db_index=True, null=True)
    is_accessory = models.BooleanField(default=False)
    MALE, FEMALE, IT, PLURAL = 'male', 'female', 'it', 'plural'
    GENDER_CHOICES = (
        (MALE, 'Мужской'),
        (FEMALE, 'Женский'),
        (IT, 'Средний'),
        (PLURAL, 'Множественное число')
    )
    default_gender = MALE
    gender_seo = models.CharField('Род/Число', max_length=50, choices=GENDER_CHOICES, default=default_gender)
    full_path_category_google = models.CharField('Категории товара в соответствии с классификацией Google',
                                                 max_length=255, null=True, blank=True,
                                                 help_text="Пример: Предметы одежды и принадлежности > Одежда > "
                                                           "Верхняя одежда > Дождевая одежда")
    image_top = models.ImageField(_('Врехнее изображение'), upload_to='categories', max_length=255, blank=True,
                                  null=True)
    brand_slug_top = models.CharField(_('Слаг для верхнего изображения'), max_length=255, db_index=True, blank=True,
                                      null=True)
    image_bottom = models.ImageField(_('Нижнее изображение'), upload_to='categories', max_length=255, blank=True,
                                     null=True)
    brand_slug_bottom = models.CharField(_('Слаг для нижнего изображения'), max_length=255, db_index=True, blank=True,
                                         null=True)

    _slug_separator = '/'
    _full_name_separator = ' > '

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return "/catalogue/{0}/".format(self.slug)

    def get_breadcrumbs(self):
        breadcrumbs_array = []
        categories = self.get_ancestors().exclude(name='_root')
        for cat in categories:
            breadcrumbs_array.append({'title': cat.name.capitalize(),
                                      'main_cat': '',
                                      'url': '/catalogue/' + cat.slug + '/',
                                      'lvl':cat.level})
        breadcrumbs_array.append({'title': self.name.capitalize(),
                                  'main_cat': '',
                                  'url': '/catalogue/' + self.slug + '/',
                                  })

        return breadcrumbs_array

    def get_show_attributes(self):
        if self.level == 2:
            return self.attributes.filter(is_main=True)
        else:
            return self.attributes.filter(is_show=True)

    def get_show_attributes_seo(self):
        return self.attributes.filter(is_show=True)

    def get_breadcrumbs_seo(self):
        breadcrumbs_array = []
        categories = self.get_ancestors().exclude(name='_root')
        for cat in categories:
            breadcrumbs_array.append({'title': cat.name.capitalize(),
                                      'main_cat': '',
                                      'url': '/catalogue/' + cat.slug + '/',
                                      'lvl': cat.level})

        breadcrumbs_array.append({'title': self.name.capitalize(),
                                      'main_cat': '',
                                      'url': '/catalogue/' + self.slug + '/',
                                      'lvl': self.level})

        return breadcrumbs_array

    def get_children_exists_product_test(self, ids):
        print(len(ids))
        return self.get_children()[:6]

    class Meta:
        app_label = 'catalogue'
        verbose_name = _('Категория')
        verbose_name_plural = _('Категории')

    class MPTTMeta:
        order_insertion_by = ['position']


class MenuCategory(models.Model):
    name = models.CharField(max_length=100, blank=True, null=True)
    category = models.OneToOneField(Category, related_name='category')
    position = models.IntegerField(default=0)

    def __str__(self):
        return self.category.name

    class Meta:
        verbose_name = 'Категория в меню'
        verbose_name_plural = 'Категории в меню'


class ProductCategory(models.Model):
    """
    Joining model between products and categories. Exists to allow customising.
    """
    product = models.ForeignKey('catalogue.Product', verbose_name=_("Product"))
    category = models.ForeignKey('catalogue.Category',
                                 verbose_name=_("Category"))

    class Meta:
        app_label = 'catalogue'
        ordering = ['product', 'category']
        unique_together = ('product', 'category')
        verbose_name = _('Категория продуктов')
        verbose_name_plural = _('Категории продуктов')

    def __str__(self):
        return "<productcategory for product '%s'>" % self.product


class Product(models.Model):
    """
    The base product object

    There's three kinds of products; they're distinguished by the structure
    field.

    - A stand alone product. Regular product that lives by itself.
    - A child product. All child products have a parent product. They're a
      specific version of the parent.
    - A parent product. It essentially represents a set of products.

    An example could be a yoga course, which is a parent product. The different
    times/locations of the courses would be associated with the child products.
    """
    STANDALONE, PARENT, CHILD = 'standalone', 'parent', 'child'
    STRUCTURE_CHOICES = (
        (STANDALONE, _('Stand-alone product')),
        (PARENT, _('Parent product')),
        (CHILD, _('Child product'))
    )
    structure = models.CharField(
        _("Product structure"), max_length=10, choices=STRUCTURE_CHOICES,
        default=STANDALONE)

    product_contractor = models.ForeignKey('catalogue.ContractorCatalogue', related_name='products_contractor',
                                           null=True, blank=True)
    # резервное название
    product_contractor_label = models.CharField(_('Contractor Label'), max_length=50, blank=True, null=True)

    upc = NullCharField(_("UPC"), max_length=64, blank=True, null=True, unique=True)

    parent = models.ForeignKey('self', null=True, blank=True, related_name='children',
                               verbose_name=_("Parent product"))

    title = models.CharField(pgettext_lazy(u'Product title', u'Title'),max_length=255, blank=True)
    short_title = models.CharField(pgettext_lazy(u'Product short title for presents', u'Short Title'),
                                   max_length=255, null=True, blank=True)
    slug = models.SlugField(_('Slug'), max_length=255, unique=False, editable=False)
    short_description = models.TextField(_('Сокращенное описание'), blank=True)
    description = models.TextField(_('Описание'), blank=True, null=True)

    product_class = models.ForeignKey(
        'catalogue.ProductClass', null=True, blank=True, on_delete=models.PROTECT,
        verbose_name=_('Product type'), related_name="products",
        help_text=_("Choose what type of product this is"))
    attributes = models.ManyToManyField('catalogue.ProductAttribute', through='ProductAttributeValue',
                                        verbose_name=_("Attributes"))
    #: It's possible to have options product class-wide, and per product.
    product_options = models.ManyToManyField('catalogue.Option', blank=True, verbose_name=_("Product options"))

    recommended_products = models.ManyToManyField('catalogue.Product', through='ProductRecommendation', blank=True,
        verbose_name=_("Recommended products"))

    gift_products = models.ManyToManyField(
        'catalogue.Product', related_name='products_gifts', through='ProductGift', blank=True)
    new_products = models.BooleanField('Новинка', default=False)

    # Denormalised product rating - used by reviews app.
    # Product has no ratings if rating is None
    rating = models.FloatField(_('Рейтинг'), null=True, editable=True)

    date_created = models.DateTimeField(_("Date created"), auto_now_add=True)

    # This field is used by Haystack to reindex search
    date_updated = models.DateTimeField(
        _("Date updated"), auto_now=True, db_index=True)

    categories = models.ManyToManyField(
        'catalogue.Category', through='ProductCategory',
        verbose_name=_("Categories"))

    is_discount = models.BooleanField(default=False)

    is_discountable = models.BooleanField(
        _("Is discountable?"), default=True, help_text=_(
            "This flag indicates if this product can be used in an offer "
            "or not"))

    product_1c_id = models.CharField(max_length=100)
    video_container = models.CharField(max_length=255, null=True, blank=True)
    price_mrc = models.DecimalField('Цена', decimal_places=2, max_digits=12, blank=True, null=True)
    price_corrected = models.DecimalField('Отткорректированная цена(для статистики)', decimal_places=2, max_digits=12, blank=True, null=True)
    price_min_market = models.DecimalField('Минимальная цена на маркете', decimal_places=2, max_digits=12, blank=True, null=True)
    model_id = models.CharField('Id модели (Яндекс.Маркет)', max_length=150, null=True, blank=True)
    item_id = models.CharField(max_length=255, null=True, blank=True)
    size_color_item_id = models.CharField(max_length=100, blank=True, null=True)
    size_item_id = models.CharField(max_length=100, blank=True, null=True)
    country_manufacter = models.CharField('Страна', max_length=100, blank=True, null=True)
    artikul = models.CharField('Артикул', max_length=128, default="")
    model_label = models.CharField('Модель', max_length=150, null=True, blank=True)
    model_id = models.CharField('Id модели (Яндекс.Маркет)', max_length=150, null=True, blank=True)
    brand = models.ForeignKey('catalogue.Brand', verbose_name='Бренд', related_name='products', null=True, blank=True)
    age = models.CharField('Возраст', max_length=50, blank=True, null=True)
    season = models.CharField('Сезон', max_length=50, blank=True, null=True)
    material = models.CharField('Материал', max_length=150, null=True, blank=True)
    size = models.CharField('Размер', max_length=50, null=True, blank=True)
    color = models.CharField('Цвет', max_length=50, null=True, blank=True)
    tax = models.IntegerField(default=0)
    is_show = models.BooleanField(default=True)
    num_in_stock = models.PositiveIntegerField(_("Number in stock"), blank=True, null=True)
    num_allocated = models.IntegerField(_("Number allocated"), blank=True, null=True)
    product_name = models.CharField('Название в именительном падеже', max_length=50, null=True, blank=True)
    price_opt = models.DecimalField('Оптовая Цена', decimal_places=2, max_digits=12, blank=True, null=True)
    old_slug = models.CharField('Старый slug товара(для редиректа со старого url на новый)', max_length=250, null=True, blank=True)
    main_image = models.CharField('Главное изображение', max_length=255, blank=True, null=True)

    producer_code = models.CharField('Код потавщика', null=True, blank=True, max_length=150,
                                     help_text="Используется для фида Google")

    brand_name = models.CharField(max_length=150, blank=True, null=True)
    category_name = models.CharField(max_length=255, blank=True, null=True)
    variant_name = models.CharField(max_length=150, blank=True, null=True)
    assortment = models.BooleanField(default=False)

    objects = ProductManager()
    browsable = BrowsableProductManager()

    class Meta:
        app_label = 'catalogue'
        # ordering = ['-date_created']
        verbose_name = 'Продукт'
        verbose_name_plural = 'Продукты'

    def get_brand_info(self):
        pav = ProductAttributeValue.objects.filter(product=self, attribute__code='brand').first()
        return Brand.objects.filter(id_option=pav.value_option_id).first() if pav else None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attr = ProductAttributesContainer(product=self)

    def __str__(self):
        if self.title:
            return self.title
        if self.attribute_summary:
            return u"%s (%s)" % (self.get_title(), self.attribute_summary)
        else:
            return self.get_title()

    def get_property_info(self):
        """Берет характеристики(значения аттрибутов) товара"""
        attributes = ProductAttributeValue.objects.filter(product=self, attribute__type_group='maincharact')
        property_info = []
        color_att = None
        season_att = None
        age_att_from = None
        age_att_to = None
        color_code, season_code, age_from_code, age_to_code = None, None, None, None
        for att in attributes:
            code = att.attribute.code
            if code == 'color1' or code == 'color2' or code == 'color3':
                if color_att:
                    color_att += ', ' + str(att.value_option)
                else:
                    if att.value_option:
                        color_att = str(att.value_option)
                color_code = 'color'

            elif code == 'season1' or code == 'season2' or code == 'season3':
                if season_att:
                    season_att += ', ' + str(att.value_option)
                else:
                    if att.value_option:
                        season_att = str(att.value_option)
                season_code = 'season'
            else:
                att_type = att.attribute.type
                curr_name = att.attribute.name
                curr_name_show = att.attribute.name_show
                if att_type == 'text':
                    curr_val = att.value_text
                elif att_type == 'integer':
                    curr_val = att.value_integer
                elif att_type == 'boolean':
                    curr_val = att.value_boolean
                elif att_type == 'float':
                    curr_val = att.value_float
                elif att_type == 'date':
                    curr_val = att.value_date
                elif att_type == 'option':
                    curr_val = att.value_option
                else:
                    curr_val = att.value_text
                if code == 'age_to' or code == 'age_from':
                    from common.views import month_to_year
                    curr_val = month_to_year(str(curr_val))
                    if code == 'age_to':
                        age_att_to = 'до ' + str(curr_val)
                        age_from_code = code
                    else:
                        age_att_from = 'от ' + str(curr_val)
                        age_to_code = code
                elif curr_val and curr_name:
                    property_info.append({'name': curr_name,
                                          'name_show': curr_name_show,
                                          'code': code,
                                          'value': curr_val})

        if color_att:
            property_info.append({'name': 'Цвет',
                                  'code': color_code,
                                  'value': color_att})
        if age_att_to and age_att_from:
            property_info.append({'name': 'Возраст',
                                  'code': age_from_code,
                                  'value': str(age_att_from) + ' ' + str(age_att_to)})
        elif age_att_to:
            property_info.append({'name': 'Возраст',
                                  'code': age_to_code,
                                  'value': str(age_att_to)})
        elif age_att_from:
            property_info.append({'name': 'Возраст',
                                  'code': age_from_code,
                                  'value': str(age_att_from)})
        if season_att:
            property_info.append({'name': 'Сезон',
                                  'code': season_code,
                                  'value': season_att})
        return property_info

    def get_provider(self):
        code = self.product_1c_id[:1]
        if code == 'l':
            return 'Лапси'
        elif code == 'r':
            return 'Рант'
        elif code == 'a':
            return 'Амата'
        elif code == 'd':
            return 'Доц'
        elif code == 't':
            return 'ТНГ'

    def get_breadcrumbs(self):
        """Генерация хлебных крошек для страниц продуктов"""
        breadcrumbs_array = []
        # Флаг равен False если товар не относится к категории 'Коляски и автокресла'
        cat_flag = False
        categories = self.categories.all()[0].get_ancestors().exclude(name='_root')
        for cat in categories:
            if str(cat.name).lower() == 'коляски и автокресла':
                cat_flag = True
            if cat_flag:
                if len(breadcrumbs_array) == 1:
                    breadcrumbs_array.append({'title': cat.name.capitalize(),
                                              'main_cat': 'main_cat',
                                              'url': '/catalogue/' + cat.slug + '/'})
                else:
                    breadcrumbs_array.append({'title': cat.name.capitalize(),
                                              'main_cat': '',
                                              'url': '/catalogue/' + cat.slug + '/'})
            else:
                if breadcrumbs_array:
                    breadcrumbs_array.append({'title': cat.name.capitalize(),
                                              'main_cat': '',
                                              'url': '/catalogue/' + cat.slug + '/'})
                else:
                    breadcrumbs_array.append({'title': cat.name.capitalize(),
                                              'main_cat': 'main_cat',
                                              'url': '/catalogue/' + cat.slug + '/'})
        breadcrumbs_array.append({'title': self.categories.all()[0].name.capitalize(),
                                  'main_cat': '',
                                  'url': '/catalogue/' + self.categories.all()[0].slug + '/'})
        breadcrumbs_array.append({'title': self.title.capitalize(),
                                  'main_cat': '',
                                  'url': '/product/' + self.slug + '_' + str(self.id) + '/'})
        return breadcrumbs_array

    def get_variants_test(self):
        return Product.objects.values('pk', 'title', 'images__original').filter(Q(item_id=self.item_id),
                                      Q(is_show=True),
                                      Q(num_in_stock__gt=0),
                                      Q(num_in_stock__gt=F('num_allocated'))). \
            exclude(id=self.pk). \
            prefetch_related('images')

    def get_variants(self):
        return Product.objects. \
            filter(Q(item_id=self.item_id),
                   Q(is_show=True),
                   Q(num_in_stock__gt=0),
                   Q(num_in_stock__gt=F(
                       'num_allocated'))).exclude(id=self.pk)

    def get_variants_for_main(self):
        return Product.objects.values('pk','item_id','images__original').\
            filter(Q(item_id=self.item_id),
                   Q(is_show=True),
                   Q(num_in_stock__gt=0),
                   Q(num_in_stock__gt=F('num_allocated')),
                   Q(images__display_order=0)).exclude(id=self.pk)

    def get_absolute_url(self):
        """
        Return a product's absolute url
        """
        return reverse('catalogue:detail',
                       kwargs={'product_slug': self.slug, 'pk': self.id})

    def clean(self):
        """
        Validate a product. Those are the rules:

        +---------------+-------------+--------------+--------------+
        |               | stand alone | parent       | child        |
        +---------------+-------------+--------------+--------------+
        | title         | required    | required     | optional     |
        +---------------+-------------+--------------+--------------+
        | product class | required    | required     | must be None |
        +---------------+-------------+--------------+--------------+
        | parent        | forbidden   | forbidden    | required     |
        +---------------+-------------+--------------+--------------+
        | stockrecords  | 0 or more   | forbidden    | 0 or more    |
        +---------------+-------------+--------------+--------------+
        | categories    | 1 or more   | 1 or more    | forbidden    |
        +---------------+-------------+--------------+--------------+
        | attributes    | optional    | optional     | optional     |
        +---------------+-------------+--------------+--------------+
        | rec. products | optional    | optional     | unsupported  |
        +---------------+-------------+--------------+--------------+
        | options       | optional    | optional     | forbidden    |
        +---------------+-------------+--------------+--------------+

        Because the validation logic is quite complex, validation is delegated
        to the sub method appropriate for the product's structure.
        """
        getattr(self, '_clean_%s' % self.structure)()
        if not self.is_parent:
            self.attr.validate_attributes()

    def _clean_standalone(self):
        """
        Validates a stand-alone product
        """
        if not self.title:
            raise ValidationError(_("Your product must have a title."))
        if not self.product_class:
            raise ValidationError(_("Your product must have a product class."))
        if self.parent_id:
            raise ValidationError(_("Only child products can have a parent."))

    def _clean_child(self):
        """
        Validates a child product
        """
        if not self.parent_id:
            raise ValidationError(_("A child product needs a parent."))
        if self.parent_id and not self.parent.is_parent:
            raise ValidationError(
                _("You can only assign child products to parent products."))
        if self.product_class:
            raise ValidationError(
                _("A child product can't have a product class."))
        if self.pk and self.categories.exists():
            raise ValidationError(
                _("A child product can't have a category assigned."))
        # Note that we only forbid options on product level
        if self.pk and self.product_options.exists():
            raise ValidationError(
                _("A child product can't have options."))

    def _clean_parent(self):
        """
        Validates a parent product.
        """
        self._clean_standalone()
        if self.has_stockrecords:
            raise ValidationError(
                _("A parent product can't have stockrecords."))

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.get_title())
        super().save(*args, **kwargs)
        # self.attr.save()

    # Properties

    @property
    def is_standalone(self):
        return self.structure == self.STANDALONE

    @property
    def is_parent(self):
        return self.structure == self.PARENT

    @property
    def is_child(self):
        return self.structure == self.CHILD

    def can_be_parent(self, give_reason=False):
        """
        Helps decide if a the product can be turned into a parent product.
        """
        reason = None
        if self.is_child:
            reason = _('The specified parent product is a child product.')
        if self.has_stockrecords:
            reason = _(
                "One can't add a child product to a product with stock"
                " records.")
        is_valid = reason is None
        if give_reason:
            return is_valid, reason
        else:
            return is_valid

    @property
    def options(self):
        """
        Returns a set of all valid options for this product.
        It's possible to have options product class-wide, and per product.
        """
        pclass_options = self.get_product_class().options.all()
        return set(pclass_options) or set(self.product_options.all())

    @property
    def is_shipping_required(self):
        return self.get_product_class().requires_shipping

    @property
    def has_stockrecords(self):
        """
        Test if this product has any stockrecords
        """
        return self.stockrecords.exists()

    @property
    def num_stockrecords(self):
        return self.stockrecords.count()

    @property
    def attribute_summary(self):
        """
        Return a string of all of a product's attributes
        """
        attributes = self.attribute_values.all()
        pairs = [attribute.summary() for attribute in attributes]
        return ", ".join(pairs)

    # The two properties below are deprecated because determining minimum
    # price is not as trivial as it sounds considering multiple stockrecords,
    # currencies, tax, etc.
    # The current implementation is very naive and only works for a limited
    # set of use cases.
    # At the very least, we should pass in the request and
    # user. Hence, it's best done as an extension to a Strategy class.
    # Once that is accomplished, these properties should be removed.

    @property
    def min_child_price_incl_tax(self):
        """
        Return minimum child product price including tax.
        """
        return self._min_child_price('incl_tax')

    @property
    def min_child_price_excl_tax(self):
        """
        Return minimum child product price excluding tax.

        This is a very naive approach; see the deprecation notice above. And
        only use it for display purposes (e.g. "new Oscar shirt, prices
        starting from $9.50").
        """
        return self._min_child_price('excl_tax')

    def _min_child_price(self, prop):
        """
        Return minimum child product price.

        This is for visual purposes only. It ignores currencies, most of the
        Strategy logic for selecting stockrecords, knows nothing about the
        current user or request, etc. It's only here to ensure
        backwards-compatibility; the previous implementation wasn't any
        better.
        """
        # strategy = Selector().strategy()
        #
        # children_stock = strategy.select_children_stockrecords(self)
        # prices = [
        #     strategy.pricing_policy(child, stockrecord)
        #     for child, stockrecord in children_stock]
        # raw_prices = sorted([getattr(price, prop) for price in prices])
        # return raw_prices[0] if raw_prices else None
        return 1

    # Wrappers for child products

    def get_title(self):
        """
        Return a product's title or it's parent's title if it has no title
        """
        title = self.title
        if not title and self.parent_id:
            title = self.parent.title
        return title

    get_title.short_description = pgettext_lazy(u"Product title", u"Title")

    def get_product_class(self):
        """
        Return a product's item class. Child products inherit their parent's.
        """
        if self.is_child:
            return self.parent.product_class
        else:
            return self.product_class

    get_product_class.short_description = _("Product class")

    def get_is_discountable(self):
        return self.is_discountable

    def get_categories(self):
        return self.categories

    get_categories.short_description = _("Categories")

    # Images

    def get_missing_image(self):
        """
        Returns a missing image object.
        """
        # This class should have a 'name' property so it mimics the Django file
        # field.
        return MissingProductImage()

    def primary_image(self):
        """
        Returns the primary image for a product. Usually used when one can
        only display one product image, e.g. in a list of products.
        """
        images = self.images.all()
        ordering = None
        if not ordering or ordering[0] != 'display_order':
            images = images.order_by('display_order')
        try:
            return images[0]
        except IndexError:
            # We return a dict with fields that mirror the key properties of
            # the ProductImage class so this missing image can be used
            # interchangeably in templates.  Strategy pattern ftw!
            return {
                'original': self.get_missing_image(),
                'caption': '',
                'is_missing': True}

    # Updating methods

    def update_rating(self):
        """
        Recalculate rating field
        """
        self.rating = self.calculate_rating()
        self.save()

    update_rating.alters_data = True

    def calculate_rating(self):
        """
        Calculate rating value
        """
        result = self.reviews.filter(
            status=self.reviews.model.APPROVED
        ).aggregate(
            sum=Sum('workmanship_score'), count=Count('id'))
        reviews_sum = result['sum'] or 0
        reviews_count = result['count'] or 0
        rating = None
        if reviews_count > 0:
            rating = float(reviews_sum) / reviews_count
        return rating

    def has_review_by(self, user):
        if user.is_anonymous():
            return False
        return self.reviews.filter(user=user).exists()

    def is_review_permitted(self, user):
        """
        Determines whether a user may add a review on this product.

        Default implementation respects OSCAR_ALLOW_ANON_REVIEWS and only
        allows leaving one review per user and product.

        Override this if you want to alter the default behaviour; e.g. enforce
        that a user purchased the product to be allowed to leave a review.
        """
        if user.is_authenticated() or settings.OSCAR_ALLOW_ANON_REVIEWS:
            return not self.has_review_by(user)
        else:
            return False

    @cached_property
    def num_approved_reviews(self):
        return self.reviews.approved().count()

    def get_related_good(self):

        return Good.objects.using('chadocontent').\
            filter(product_contractor=self.product_1c_id).first()

    @property
    def get_size_value(self):
        size = self.attribute_values.filter(attribute__code='size')
        # size_val = ProductAttributeValue.objects.filter(product=self,attribute__code='size')
        return size[0].value_option.show_value if size else None

    def get_current_sizes(self):
        if self.size_item_id:
            size_products = Product.objects.filter(size_item_id=self.size_item_id)
            prod_values = ProductAttributeValue.objects.filter(product__in=size_products, attribute__code='size').order_by('value_option__minimum')
            current_sizes = [[p.value_option.show_value, p.product.pk] for p in prod_values]
            return current_sizes
        else:
            return []

    def get_sizes_category(self):
        if self.size_item_id:
            size_products = Product.objects.filter(Q(size_item_id=self.size_item_id),
                                                   Q(num_in_stock__gt=0),
                                                   Q(num_in_stock__gt=F('num_allocated')))
            prod_values = ProductAttributeValue.objects.filter(product__in=size_products, attribute__code='size').order_by('value_option__minimum')
            current_sizes = [[p.value_option.show_value, p.product.pk] for p in prod_values]
            return current_sizes
        else:
            return []

    def get_stock_status(self):
        return Product.objects.filter(Q(id=self.id),Q(num_in_stock__gt=0),Q(num_in_stock__gt=F('num_allocated'))).exists()

    def get_active_discount(self):
        current_now = timezone.now()
        return self.discounts.filter(start_datetime__lte=current_now, end_datetime__gte=timezone.now()).first()

    def get_discount(self):
        current_now = timezone.now()
        discount = self.discounts.filter(start_datetime__lte=current_now, end_datetime__gte=timezone.now()).first()
        return discount if discount else None

    def get_discount_price(self):
        discount = self.get_discount()
        if discount:
            return math.ceil(float(self.price_mrc - (self.price_mrc * discount.discount_value) / 100))
        else:
            return self.price_mrc

    def is_discountable_status(self):
        current_now = timezone.now()
        return self.discounts.filter(start_datetime__lte=current_now, end_datetime__gte=timezone.now()).exists()

    def get_attribute_value(self, attr_code):

        return self.attr_code


class ProductRecommendation(models.Model):
    """
    'Through' model for product recommendations
    """
    primary = models.ForeignKey('catalogue.Product', related_name='primary_recommendations',
                                verbose_name=_("Primary product"))
    recommendation = models.ForeignKey('catalogue.Product', verbose_name=_("Recommended product"))
    ranking = models.PositiveSmallIntegerField(_('Ranking'), default=0)
    weight = models.PositiveSmallIntegerField(_('Weight'), default=0)

    def __str__(self):
        return str(self.pk)

    def save(self, *args, **kwargs):
        max_ranking_info = ProductRecommendation.objects.filter(primary=self.primary).aggregate(Max('ranking'))
        max_ranking = max_ranking_info.get('ranking__max') or 0
        self.ranking = max_ranking + 1
        super().save(*args,**kwargs)

    class Meta:
        app_label = 'catalogue'
        ordering = ['primary', 'ranking']
        unique_together = ('primary', 'recommendation')
        verbose_name = _('Product recommendation')
        verbose_name_plural = _('Product recomendations')


class ProductAttribute(models.Model):
    category = models.ManyToManyField('catalogue.Category', through='catalogue.ProductAttributeCategory',
                                      related_name='attributes')
    name = models.CharField(_('Name'), max_length=128)
    name_show = models.CharField(_('Название отображаемое на сайте'), max_length=128, blank=True, null=True)
    code = models.SlugField(
        _('Code'), max_length=128,
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z_][0-9a-zA-Z_-]*$',
                message=_(
                    "Code can only contain the letters a-z, A-Z, digits, "
                    "and underscores, and can't start with a digit.")),
            non_python_keyword
        ])

    # Attribute types
    TEXT = "text"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    FLOAT = "float"
    RICHTEXT = "richtext"
    DATE = "date"
    OPTION = "option"
    ENTITY = "entity"
    FILE = "file"
    IMAGE = "image"
    TYPE_CHOICES = (
        (TEXT, _("Text")),
        (INTEGER, _("Integer")),
        (BOOLEAN, _("True / False")),
        (FLOAT, _("Float")),
        (RICHTEXT, _("Rich Text")),
        (DATE, _("Date")),
        (OPTION, _("Option")),
        (ENTITY, _("Entity")),
        (FILE, _("File")),
        (IMAGE, _("Image")),
    )
    type = models.CharField(
        choices=TYPE_CHOICES, default=TYPE_CHOICES[0][0],
        max_length=20, verbose_name=_("Type"))

    option_group = models.ForeignKey(
        'catalogue.ProductAttributeOptionGroup', blank=True, null=True,verbose_name=_("Option Group"))
    required = models.BooleanField(_('Required'), default=False)
    id_attribute = models.IntegerField(blank=True)
    display_order = models.PositiveIntegerField(default=0)
    legend = models.CharField(max_length=255, null=True, blank=True)
    MAINCHARACT = 'maincharact'
    TRANSCHARACT = 'transcharact'
    TYPE_GROUP_CHOICES = (
        (MAINCHARACT, 'Главные характеристики'),
        (TRANSCHARACT, 'Транспортные характеристики'),
    )

    type_group = models.CharField(max_length=50, choices=TYPE_GROUP_CHOICES,
                                  default=MAINCHARACT)
    CHECKBOX_LIST = 'checkbox_list'
    SELECT_LIST = 'select_list'
    SLIDER_INPUT = 'slider_input'
    WIDGET_TYPE_CHOICES = (
        (CHECKBOX_LIST, 'Чекбоксы'),
        (SELECT_LIST, 'Селектор'),
        (SLIDER_INPUT, 'Ползунок'),
    )
    widget_type_display = models.CharField(max_length=50, choices=WIDGET_TYPE_CHOICES,
                                           default=CHECKBOX_LIST)
    is_show = models.BooleanField(default=False)
    is_main = models.BooleanField(default=False)

    class Meta:
        app_label = 'catalogue'
        ordering = ['display_order']
        verbose_name = 'Атрибут продукта'
        verbose_name_plural = 'Атрибуты продуктов'

    @property
    def is_option(self):
        return self.type == self.OPTION

    @property
    def is_file(self):
        return self.type in [self.FILE, self.IMAGE]

    def __str__(self):
        return self.name

    def save_value(self, product, value):

        ProductAttributeValue = get_model('catalogue', 'ProductAttributeValue')
        try:
            value_obj = product.attribute_values.get(attribute=self)
        except ProductAttributeValue.DoesNotExist:
            delete_file = self.is_file and value is False
            if value is None or value == '' or delete_file:
                return
            value_obj = ProductAttributeValue.objects.create(
                product=product, attribute=self)

        if self.is_file:
            if value is None:
                # No change
                return
            elif value is False:
                # Delete file
                value_obj.delete()
            else:
                # New uploaded file
                value_obj.value = value
                value_obj.save()
        else:
            if value is None or value == '':
                value_obj.delete()
                return
            if value != value_obj.value:
                value_obj.value = value
                value_obj.save()

    def validate_value(self, value):
        validator = getattr(self, '_validate_%s' % self.type)
        validator(value)

    # Validators

    def _validate_text(self, value):
        if not isinstance(value, six.string_types):
            raise ValidationError(_("Must be str or unicode"))

    _validate_richtext = _validate_text

    def _validate_float(self, value):
        try:
            float(value)
        except ValueError:
            raise ValidationError(_("Must be a float"))

    def _validate_integer(self, value):
        try:
            int(value)
        except ValueError:
            raise ValidationError(_("Must be an integer"))

    def _validate_date(self, value):
        if not (isinstance(value, datetime) or isinstance(value, date)):
            raise ValidationError(_("Must be a date or datetime"))

    def _validate_boolean(self, value):
        if not type(value) == bool:
            raise ValidationError(_("Must be a boolean"))

    def _validate_entity(self, value):
        if not isinstance(value, models.Model):
            raise ValidationError(_("Must be a model instance"))

    def _validate_option(self, value):
        if not isinstance(value, get_model('catalogue', 'ProductAttributeOption')):
            raise ValidationError(
                _("Must be an ProductAttributeOption model object instance"))
        if not value.pk:
            raise ValidationError(_("ProductAttributeOption has not been saved yet"))
        valid_values = self.option_group.options.values_list(
            'option', flat=True)
        if value.option not in valid_values:
            raise ValidationError(
                _("%(enum)s is not a valid choice for %(attr)s") %
                {'enum': value, 'attr': self})

    def _validate_file(self, value):
        if value and not isinstance(value, File):
            raise ValidationError(_("Must be a file field"))

    _validate_image = _validate_file


class ProductAttributeValue(models.Model):
    """
    The "through" model for the m2m relationship between catalogue.Product and
    catalogue.ProductAttribute.  This specifies the value of the attribute for
    a particular product

    For example: number_of_pages = 295
    """
    attribute = models.ForeignKey(
        'catalogue.ProductAttribute', verbose_name=_("Attribute"))
    product = models.ForeignKey(
        'catalogue.Product', related_name='attribute_values',
        verbose_name=_("Product"))

    value_text = models.TextField(_('Text'), blank=True, null=True)
    value_integer = models.IntegerField(_('Integer'), blank=True, null=True)
    value_boolean = models.NullBooleanField(_('Boolean'), blank=True)
    value_float = models.FloatField(_('Float'), blank=True, null=True)
    value_richtext = models.TextField(_('Richtext'), blank=True, null=True)
    value_date = models.DateField(_('Date'), blank=True, null=True)
    value_option = models.ForeignKey(
        'catalogue.ProductAttributeOption', blank=True, null=True,
        verbose_name=_("Value option"))
    value_file = models.FileField(
        upload_to=settings.OSCAR_IMAGE_FOLDER, max_length=255,
        blank=True, null=True)
    value_image = models.ImageField(
        upload_to=settings.OSCAR_IMAGE_FOLDER, max_length=255,
        blank=True, null=True)
    value_entity = GenericForeignKey(
        'entity_content_type', 'entity_object_id')

    entity_content_type = models.ForeignKey(
        ContentType, null=True, blank=True, editable=False)
    entity_object_id = models.PositiveIntegerField(
        null=True, blank=True, editable=False)

    id_attribute_value = models.IntegerField(null=True, blank=True)


    def _get_value(self):
            return getattr(self, 'value_%s' % self.attribute.type)

    def _set_value(self, new_value):
        if self.attribute.is_option and isinstance(new_value, six.string_types):
            # Need to look up instance of AttributeOption
            new_value = self.attribute.option_group.options.get(
                option=new_value)
        setattr(self, 'value_%s' % self.attribute.type, new_value)

    value = property(_get_value, _set_value)

    class Meta:
        app_label = 'catalogue'
        unique_together = ('attribute', 'product')
        verbose_name = 'Значение атрибута продукта'
        verbose_name_plural = 'Значения атрибутов продуктов'

    def __str__(self):
        return self.summary()

    def summary(self):
        """
        Gets a string representation of both the attribute and it's value,
        used e.g in product summaries.
        """
        return u"%s: %s" % (self.attribute.name, self.value_as_text)

    @property
    def value_as_text(self):
        """
        Returns a string representation of the attribute's value. To customise
        e.g. image attribute values, declare a _image_as_text property and
        return something appropriate.
        """
        property_name = '_%s_as_text' % self.attribute.type
        return getattr(self, property_name, self.value)

    @property
    def _richtext_as_text(self):
        return strip_tags(self.value)

    @property
    def _entity_as_text(self):
        """
        Returns the unicode representation of the related model. You likely
        want to customise this (and maybe _entity_as_html) if you use entities.
        """
        return six.text_type(self.value)

    @property
    def value_as_html(self):
        """
        Returns a HTML representation of the attribute's value. To customise
        e.g. image attribute values, declare a _image_as_html property and
        return e.g. an <img> tag.  Defaults to the _as_text representation.
        """
        property_name = '_%s_as_html' % self.attribute.type
        return getattr(self, property_name, self.value_as_text)

    @property
    def _richtext_as_html(self):
        return mark_safe(self.value)


class ProductAttributeCategory(models.Model):
    attribute = models.ForeignKey('catalogue.ProductAttribute')
    category = models.ForeignKey(Category)

    def __str__(self):
        return '{}-{}'.format(self.attribute.name, self.category.name)

    class Meta:
        ordering = ['attribute', 'category']
        unique_together = ('attribute', 'category')
        verbose_name = 'Атрибуты/Категории'
        verbose_name_plural = 'Атрибуты/Категории'


class ProductAttributeOptionGroup(models.Model):
    name = models.CharField(_('Name'), max_length=128, null=True, blank=True)
    code = models.SlugField(_("Code"), max_length=128)

    def __str__(self):
        return self.name

    class Meta:
        app_label = 'catalogue'
        verbose_name = _('Attribute option group')
        verbose_name_plural = _('Attribute option groups')

    @property
    def option_summary(self):
        options = [o.option for o in self.options.all()]
        return ", ".join(options)

    @property
    def color_options(self):
        return self.options.order_by('option')

    @property
    def default_options_order(self):
        return self.options.order_by('option')

    @property
    def size_options_order(self):
        return self.options.order_by('minimum')


class ProductAttributeOption(models.Model):
    """
    Provides an option within an option group for an attribute type
    Examples: In a Language group, English, Greek, French
    """
    group = models.ForeignKey(
        'catalogue.ProductAttributeOptionGroup', related_name='options',
        verbose_name=_("Group"))
    option = models.CharField(_('Option'), max_length=255)
    id_attribute_option = models.IntegerField()
    minimum = models.FloatField('Значение от', default=0.00, help_text='Сейчас используется только для размеров')
    maximum = models.FloatField('Значение до', default=0.00, help_text='Сейчас используется только для размеров')
    show_value = models.CharField(max_length=255, null=True, blank=True)
    # Падежи для мужского рода
    case_i = models.CharField('В именительном падеже в мужском роде', max_length=255, null=True, blank=True)
    case_r = models.CharField('В родительном падеже в мужском роде', max_length=255, null=True, blank=True)
    case_v = models.CharField('В винительном падеже в мужском роде', max_length=255, null=True, blank=True)
    case_d = models.CharField('В дательном падеже в мужском роде', max_length=255, null=True, blank=True)
    case_p = models.CharField('В предложном падеже в мужском роде', max_length=255, null=True, blank=True)
    case_t = models.CharField('В творительном падеже в мужском роде', max_length=255, null=True, blank=True)
    # Падежи для женского рода
    case_i_g = models.CharField('В именительном падеже в женском роде', max_length=255, null=True, blank=True)
    case_r_g = models.CharField('В родительном падеже в женском роде', max_length=255, null=True, blank=True)
    case_v_g = models.CharField('В винительном падеже в женском роде', max_length=255, null=True, blank=True)
    case_d_g = models.CharField('В дательном падеже в женском роде', max_length=255, null=True, blank=True)
    case_p_g = models.CharField('В предложном падеже в женском роде', max_length=255, null=True, blank=True)
    case_t_g = models.CharField('В творительном падеже в женском роде', max_length=255, null=True, blank=True)
    # Падежи для среднего рода
    case_i_it = models.CharField('В именительном падеже в среднем роде', max_length=255, null=True, blank=True)
    case_r_it = models.CharField('В родительном падеже в среднем роде', max_length=255, null=True, blank=True)
    case_v_it = models.CharField('В винительном падеже в среднем роде', max_length=255, null=True, blank=True)
    case_d_it = models.CharField('В дательном падеже в среднем роде', max_length=255, null=True, blank=True)
    case_p_it = models.CharField('В предложном падеже в среднем роде', max_length=255, null=True, blank=True)
    case_t_it = models.CharField('В творительном падеже в среднем роде', max_length=255, null=True, blank=True)
    # Падежи для множественного числа
    case_i_m = models.CharField('Во множественном числе им. падеже', max_length=255, null=True, blank=True)
    case_r_m = models.CharField('Во множественном числе род. падеже', max_length=255, null=True, blank=True)
    case_v_m = models.CharField('Во множественном числе вин. падеже', max_length=255, null=True, blank=True)
    case_d_m = models.CharField('Во множественном числе дат. падеже', max_length=255, null=True, blank=True)
    case_p_m = models.CharField('Во множественном числе пред. падеже', max_length=255, null=True, blank=True)
    case_t_m = models.CharField('Во множественном числе твор. падеже', max_length=255, null=True, blank=True)
    # Существительное(к нему не применяются падежи)
    case_noun = models.CharField('Существительное', max_length=255, null=True, blank=True)
    color_code = models.CharField(max_length=30, null=True, blank=True)
    display_order = models.PositiveIntegerField('Позиция', default=0)

    def __str__(self):
        if self.group.code == 'size':
            return self.show_value
        else:
            return self.option

    class Meta:
        app_label = 'catalogue'
        ordering = ('option',)
        unique_together = ('group', 'option')
        verbose_name = 'Опция атрибута'
        verbose_name_plural = 'Опции для атрибутов'


class Option(models.Model):
    """
    An option that can be selected for a particular item when the product
    is added to the basket.

    For example,  a list ID for an SMS message send, or a personalised message
    to print on a T-shirt.

    This is not the same as an 'attribute' as options do not have a fixed value
    for a particular item.  Instead, option need to be specified by a customer
    when they add the item to their basket.
    """
    name = models.CharField(_("Name"), max_length=128)
    code = AutoSlugField(_("Code"), max_length=128, unique=True,
                         populate_from='name')

    REQUIRED, OPTIONAL = ('Required', 'Optional')
    TYPE_CHOICES = (
        (REQUIRED, _("Required - a value for this option must be specified")),
        (OPTIONAL, _("Optional - a value for this option can be omitted")),
    )
    type = models.CharField(_("Status"), max_length=128, default=REQUIRED,
                            choices=TYPE_CHOICES)

    class Meta:
        app_label = 'catalogue'
        verbose_name = _("Option")
        verbose_name_plural = _("Options")

    def __str__(self):
        return self.name

    @property
    def is_required(self):
        return self.type == self.REQUIRED


class MissingProductImage(object):
    """
    Mimics a Django file field by having a name property.

    sorl-thumbnail requires all it's images to be in MEDIA_ROOT. This class
    tries symlinking the default "missing image" image in STATIC_ROOT
    into MEDIA_ROOT for convenience, as that is necessary every time an Oscar
    project is setup. This avoids the less helpful NotFound IOError that would
    be raised when sorl-thumbnail tries to access it.
    """

    def __init__(self, name=None):
        self.name = name if name else settings.OSCAR_MISSING_IMAGE_URL
        media_file_path = os.path.join(settings.MEDIA_ROOT, self.name)
        # don't try to symlink if MEDIA_ROOT is not set (e.g. running tests)
        if settings.MEDIA_ROOT and not os.path.exists(media_file_path):
            self.symlink_missing_image(media_file_path)

    def symlink_missing_image(self, media_file_path):
        static_file_path = find('oscar/img/%s' % self.name)
        if static_file_path is not None:
            try:
                os.symlink(static_file_path, media_file_path)
            except OSError:
                raise ImproperlyConfigured((
                                               "Please copy/symlink the "
                                               "'missing image' image at %s into your MEDIA_ROOT at %s. "
                                               "This exception was raised because Oscar was unable to "
                                               "symlink it for you.") % (media_file_path,
                                                                         settings.MEDIA_ROOT))
            else:
                logging.info((
                                 "Symlinked the 'missing image' image at %s into your "
                                 "MEDIA_ROOT at %s") % (media_file_path,
                                                        settings.MEDIA_ROOT))


class ProductImage(models.Model):
    """
    An image of a product
    """
    product = models.ForeignKey(
        'catalogue.Product', related_name='images', verbose_name=_("Product"))
    original = models.ImageField(
        _("Original"), upload_to=settings.OSCAR_IMAGE_FOLDER, max_length=255)
    caption = models.CharField(_("Caption"), max_length=200, blank=True)

    #: Use display_order to determine which is the "primary" image
    display_order = models.PositiveIntegerField(
        _("Display order"), default=0,
        help_text=_("An image with a display order of zero will be the primary"
                    " image for a product"))
    date_created = models.DateTimeField(_("Date created"), auto_now_add=True)
    img_good_pk = models.CharField(max_length=10, blank=True, null=True)
    is_check = models.BooleanField(default=False)

    class Meta:
        app_label = 'catalogue'
        # Any custom models should ensure that this ordering is unchanged, or
        # your query count will explode. See AbstractProduct.primary_image.
        ordering = ["display_order"]
        # unique_together = ("product", "display_order")
        verbose_name = _('Изображение продукта')
        verbose_name_plural = _('Изображения продуктов')

    def __str__(self):
        return u"Image of '%s'" % self.product

    def is_primary(self):
        """
        Return bool if image display order is 0
        """
        return self.display_order == 0

    def delete(self, *args, **kwargs):
        """
        Always keep the display_order as consecutive integers. This avoids
        issue #855.
        """
        super().delete(*args, **kwargs)
        for idx, image in enumerate(self.product.images.all()):
            image.display_order = idx
            image.save()


class ProductGift(models.Model):
    primary_gift = models.ForeignKey('catalogue.Product', related_name='primary_gifts')
    gift = models.ForeignKey('catalogue.Product')
    ranking = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['primary_gift', '-ranking']
        unique_together = ('primary_gift', 'gift')
        verbose_name = 'Подарок к товару'
        verbose_name_plural = 'Подарки к товару'


class Brand(models.Model):
    name = models.CharField(_('Название'), max_length=255, db_index=True)
    image = models.ImageField(_('Изображение'), upload_to='brands', blank=True,
                              null=True, max_length=255)
    description = models.TextField(_('Описание бренда'), blank=True, null=True)
    display_order = models.PositiveIntegerField(
        _("Последовательность вывода"), default=100,
        help_text=_("Бренд со значением поле 0 будет первым и т.д. (по умолчанию 100)"
                    ""))
    slug = models.SlugField(_('Slug'), max_length=255, unique=True, null=True)
    name_original = models.CharField(_('Название в оригинале'), max_length=255, db_index=True)
    name_ru = models.CharField(_('Название на русском'), max_length=255, db_index=True)
    name_ru_bracket = models.CharField(_('Для русских брендов'), max_length=255, blank=True)
    id_option = models.IntegerField(default=0)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return "{0}{1}/".format(reverse('brand_list'), self.slug)

    class Meta:
        app_label = 'catalogue'
        verbose_name = 'Бренд'
        verbose_name_plural = 'Бренды'


class FilterItem(models.Model):
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=150)
    show = models.BooleanField(default=True)
    position = models.IntegerField(default=0)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('position',)
        verbose_name = 'Фильтр'
        verbose_name_plural = 'Фильтры'


class FilterItemValue(models.Model):
    value_str = models.CharField(max_length=255, null=True, blank=True)
    value_integer = models.IntegerField(null=True)
    filter_item = models.ForeignKey(FilterItem, related_name='filter_item_values')
    position = models.IntegerField()

    def __str__(self):
        return self.value_str


class ContractorCatalogue(models.Model):
    address = models.CharField(_('Address'), max_length=255, db_index=True)
    fio = models.CharField(_('FIO'), max_length=255, db_index=True)
    organization = models.CharField(_('Organization'), max_length=255, db_index=True)
    phone = models.CharField(_('Phone'), max_length=255, db_index=True)
    additional_comment = models.CharField(_('Additional comment'), max_length=255, blank=True, null=True)
    post_code = models.CharField(_('Post code'), max_length=255, db_index=True)
    city = models.ForeignKey(Spsr_city, null=True, on_delete=models.SET_NULL)
    address_type = models.IntegerField(_('address type'), default=8)
    sbor_addr_id = models.CharField(_('ID address'), max_length=11, null=True, blank=True)
    sbor_addr_owner_id = models.CharField(_('Owner Id address'), max_length=11, null=True, blank=True)
    email = models.CharField(_("Email"), max_length=250, null=True, blank=True)
    code = models.CharField(max_length=100, null=True, blank=True)
    cm_code = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return self.organization if self.organization else str(self.pk)

    class Meta:
        app_label = 'catalogue'
        verbose_name = 'Поставщик'
        verbose_name_plural = 'Поставщики'
