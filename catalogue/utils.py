import os
import shutil
import tarfile
import tempfile
import zipfile
import zlib
import datetime
from PIL import Image

from django.core.exceptions import FieldError
from django.core.files import File
from django.db.transaction import atomic
from django.utils.translation import ugettext_lazy as _
from django.db.models import Q, F

from .exceptions import (
    IdenticalImageError, ImageImportError, InvalidImageArchive)

from catalogue.models import Category, Product, ProductImage


class Importer(object):

    allowed_extensions = ['.jpeg', '.jpg', '.gif', '.png']

    def __init__(self, logger, field):
        self.logger = logger
        self._field = field

    @atomic  # noqa (too complex (10))
    def handle(self, dirname):
        stats = {
            'num_processed': 0,
            'num_skipped': 0,
            'num_invalid': 0}
        image_dir, filenames = self._get_image_files(dirname)
        if image_dir:
            for filename in filenames:
                try:
                    lookup_value \
                        = self._get_lookup_value_from_filename(filename)
                    self._process_image(image_dir, filename, lookup_value)
                    stats['num_processed'] += 1
                except Product.MultipleObjectsReturned:
                    self.logger.warning("Multiple products matching %s='%s',"
                                        " skipping"
                                        % (self._field, lookup_value))
                    stats['num_skipped'] += 1
                except Product.DoesNotExist:
                    self.logger.warning("No item matching %s='%s'"
                                        % (self._field, lookup_value))
                    stats['num_skipped'] += 1
                except IdenticalImageError:
                    self.logger.warning("Identical image already exists for"
                                        " %s='%s', skipping"
                                        % (self._field, lookup_value))
                    stats['num_skipped'] += 1
                except IOError as e:
                    stats['num_invalid'] += 1
                    raise ImageImportError(_('%(filename)s is not a valid'
                                             ' image (%(error)s)')
                                           % {'filename': filename,
                                              'error': e})
                except FieldError as e:
                    raise ImageImportError(e)
            if image_dir != dirname:
                shutil.rmtree(image_dir)
        else:
            raise InvalidImageArchive(_('%s is not a valid image archive')
                                      % dirname)
        self.logger.info("Finished image import: %(num_processed)d imported,"
                         " %(num_skipped)d skipped" % stats)

    def _get_image_files(self, dirname):
        filenames = []
        image_dir = self._extract_images(dirname)
        if image_dir:
            for filename in os.listdir(image_dir):
                ext = os.path.splitext(filename)[1]
                if os.path.isfile(os.path.join(image_dir, filename)) \
                        and ext in self.allowed_extensions:
                    filenames.append(filename)
        return image_dir, filenames

    def _extract_images(self, dirname):
        '''
        Returns path to directory containing images in dirname if successful.
        Returns empty string if dirname does not exist, or could not be opened.
        Assumes that if dirname is a directory, then it contains images.
        If dirname is an archive (tar/zip file) then the path returned is to a
        temporary directory that should be deleted when no longer required.
        '''
        if os.path.isdir(dirname):
            return dirname

        ext = os.path.splitext(dirname)[1]
        if ext in ['.gz', '.tar']:
            image_dir = tempfile.mkdtemp()
            try:
                tar_file = tarfile.open(dirname)
                tar_file.extractall(image_dir)
                tar_file.close()
                return image_dir
            except (tarfile.TarError, zlib.error):
                return ""
        elif ext == '.zip':
            image_dir = tempfile.mkdtemp()
            try:
                zip_file = zipfile.ZipFile(dirname)
                zip_file.extractall(image_dir)
                zip_file.close()
                return image_dir
            except (zlib.error, zipfile.BadZipfile, zipfile.LargeZipFile):
                return ""
        # unknown archive - perhaps this should be treated differently
        return ""

    def _process_image(self, dirname, filename, lookup_value):
        file_path = os.path.join(dirname, filename)
        trial_image = Image.open(file_path)
        trial_image.verify()

        kwargs = {self._field: lookup_value}
        item = Product._default_manager.get(**kwargs)

        new_data = open(file_path, 'rb').read()
        next_index = 0
        for existing in item.images.all():
            next_index = existing.display_order + 1
            try:
                if new_data == existing.original.read():
                    raise IdenticalImageError()
            except IOError:
                # File probably doesn't exist
                existing.delete()

        new_file = File(open(file_path, 'rb'))
        im = ProductImage(product=item, display_order=next_index)
        im.original.save(filename, new_file, save=False)
        im.save()
        self.logger.debug('Image added to "%s"' % item)

    def _fetch_item(self, filename):
        kwargs = {self._field: self._get_lookup_value_from_filename(filename)}
        return Product._default_manager.get(**kwargs)

    def _get_lookup_value_from_filename(self, filename):
        return os.path.splitext(filename)[0]


def get_categories_with_products_new(categories_list):
    categories_ids = []
    for cat in categories_list:
        for c in cat.get_children():
            children = c.get_children()
            categories_ids.append(c.id)

    prod_categories_all = Product.objects.values('categories__id', 'categories__parent').\
                                        filter(Q(num_in_stock__gt=0),
                                               Q(num_in_stock__gt=F('num_allocated')))

    prod_categories = set()
    for id in prod_categories_all:
        prod_categories.add(id['categories__parent'])
        prod_categories.add(id['categories__id'])

    result_ids = []
    for c in categories_ids:
        if c in prod_categories:
            result_ids.append(c)

    categories_with_products = Category.objects.prefetch_related('children').\
        filter(pk__in=result_ids).order_by('lft')

    print("step", str(datetime.datetime.now()))
    return categories_with_products


def get_categories_with_products(categories_list):
    categories_ids = []
    for cat in categories_list:
        for c in cat.get_children():
            if c.get_children():
                j = len(c.get_children())
                count = j
                for c_sub in c.get_children():
                    products = Product.objects.filter(Q(categories=c_sub.id),
                                                      Q(stockrecords__num_in_stock__gt=0),
                                                      Q(stockrecords__num_in_stock__gt=F('stockrecords__num_allocated'))).\
                        prefetch_related('categories','images', 'stockrecords')
                    if products and len(products) > 0:
                       j -= 1
                if j < count:
                    categories_ids.append(c.id)
            else:
                products = Product.objects.filter(Q(categories=c.id),
                                                  Q(stockrecords__num_in_stock__gt=0),
                                                  Q(stockrecords__num_in_stock__gt=F('stockrecords__num_allocated'))).\
                    prefetch_related('categories','images', 'stockrecords')
                if products and len(products) > 0:
                    categories_ids.append(c.id)

    categories_with_products = Category.objects.prefetch_related('children').\
        filter(pk__in=categories_ids).order_by('lft')
    return categories_with_products


def get_categories_with_products_for_ids(categories_ids):
    full_categories_ids = []
    category_all = Category.objects.select_related('parent').filter(pk__in=categories_ids)
    products_all = Product.objects.\
        filter(Q(num_in_stock__gt=F('num_allocated')), Q(num_in_stock__gt=0), Q(categories__in=category_all))
    for id in categories_ids:
        category = category_all.get(pk=id)
        category_childs = category.get_children()
        if category_childs:
            j = len(category_childs)
            count = j
            for c_sub in category_childs:
                products = products_all.filter(Q(categories=c_sub.id))
                if products and len(products) > 0:
                    j -= 1
            if j < count:
                full_categories_ids.append(category.id)
        else:
            products = products_all.filter(Q(categories=id))
            if products and len(products) > 0:
                full_categories_ids.append(id)
    if len(full_categories_ids) > 0:
        categories_with_products = category_all.filter(pk__in=full_categories_ids).order_by('lft')
    else:
        categories_with_products = ''
    return categories_with_products


def get_categories_with_all_products_for_ids(categories_ids):
    full_categories_ids = []
    category_all = Category.objects.select_related('parent').filter(pk__in=categories_ids)
    products_all = Product.objects.prefetch_related('categories').filter(Q(categories__in=category_all))
    for id in categories_ids:
        category = category_all.get(pk=id)
        category_childs = category.get_children()
        if category_childs:
            j = len(category_childs)
            count = j
            for c_sub in category_childs:
                products = Product.objects.filter(Q(categories=c_sub.id))
                if products and len(products) > 0:
                    j -= 1
            if j < count:
                full_categories_ids.append(category.id)
        else:
            products = Product.objects.filter(Q(categories=id))
            if products and len(products) > 0:
                full_categories_ids.append(id)
    if len(full_categories_ids) > 0:
        categories_with_products = category_all.filter(pk__in=full_categories_ids).order_by('lft')
    else:
        categories_with_products = ''

    return categories_with_products


def get_categories_with_products_for_ids_new(categories_ids):
    print("Zapros", str(datetime.datetime.now()))
    full_categories_ids = []
    for category in categories_ids:
        if category.get_children():
            child_ids = [c.pk for c in category.get_children()]
            is_exists = Product.objects.filter(
                Q(num_in_stock__gt=F('num_allocated')),
                Q(categories__in=child_ids),
                Q(num_in_stock__gt=0)).exists()
        else:
            is_exists = Product.objects.filter(Q(num_in_stock__gt=F('num_allocated')),
                                                  Q(categories=category.id),
                                                  Q(num_in_stock__gt=0)).exists()
        if is_exists:
            full_categories_ids.append(category.id)
    if len(full_categories_ids) > 0:
        categories_with_products = Category.objects.select_related('parent').\
            filter(pk__in=full_categories_ids).\
            order_by('lft')
    else:
        categories_with_products = ''

    return categories_with_products


