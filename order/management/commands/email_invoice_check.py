import xlrd
import os
from datetime import timedelta, date
from imbox import Imbox
from django.conf import settings
from django.core.management.base import BaseCommand
from order.models import Order, OrderStatus
"""
Слабое место скрипта - сверка происходит исключительно по суммам внутри накладной и
в таблице order_order. При большом количестве заказов логику следует улучшить.
"""

class Command(BaseCommand):
    order_delivered        = OrderStatus.objects.filter(display_name='order_delivered').first() #15
    ord_deliv_pay_rec      = OrderStatus.objects.filter(display_name='order_delivered_payment_received').first() #21
    ord_deliv_pay_rec_spsr = OrderStatus.objects.filter(display_name='order_delivered_payment_from_spsr_received').first() #22
    payment_card = 1
    payment_on_delivery = 2
    delivered = Order.objects.filter(status=order_delivered.pk)
    files = []

    def handle(self, *args, **options):
        print("--- Выполняется ---")
        for deliver in self.delivered:
            if deliver.payment_type_id == self.payment_card:
                if deliver.status_id == self.order_delivered.pk:
                    deliver.status_id = self.ord_deliv_pay_rec.pk
                    deliver.save()
        self.get_xls_from_emails()
        self.finalize_order_status()
        self.remove_xls_files()
        print("---- Завершено ----")                
    
    def get_xls_from_emails(self, *args, **options):
        imbox = Imbox('imap.yandex.ru', username='office@chadomarket.ru',
                      password='brTES32lsld3AZ', ssl=True,
                      ssl_context=None, port=993
                      )
        yesterday = date.today() - timedelta(1) #За сутки
        count = 0
        all_messages = imbox.messages(sent_from='kostyuchek_aa@spsr.ru', date__gt=yesterday)
        for uid, msg in all_messages:
            count += 1
            for attach in msg.attachments:
                filename_raw = attach.get('filename').replace('"','')
                filename = os.path.join(settings.ROOT_DIR,'0{}.xls'.format(count))
                self.files.append(filename)
                fp = open(filename, 'wb')
                fp.write(attach.get('content').read())
                fp.close()
        all_messages = imbox.messages(sent_from='kostyuchek_aa@cpcr.ru', date__gt=yesterday)
        for uid, msg in all_messages:
            count += 1
            for attach in msg.attachments:
                filename_raw = attach.get('filename').replace('"','')
                filename = os.path.join(settings.ROOT_DIR,'0{}.xls'.format(count))
                self.files.append(filename)
                fp = open(filename, 'wb')
                fp.write(attach.get('content').read())
                fp.close()

    def finalize_order_status(self, *args, **options):
        for file in self.files:
            print("Название файла:", file)
            book = xlrd.open_workbook(file)
            sh = book.sheet_by_index(0)
            #Для каждой накладной внутри файла
            for i in range(int(sh.cell_value(rowx=sh.nrows-11, colx=0))):
                invoice_num = sh.cell_value(rowx=6, colx=1)
                if sh.ncols == 12:
                    invoice_sum = int(sh.cell_value(rowx=6+i, colx=5))
                elif sh.ncols == 10:
                    invoice_sum = int(sh.cell_value(rowx=6+i, colx=4))
                else:
                    print("Неизвестный формат накладной")
                for deliver in self.delivered:
                    if deliver.total_incl_tax == invoice_sum:
                        if deliver.payment_type_id == self.payment_on_delivery:
                            if deliver.status_id == self.order_delivered.pk:
                                print("Изменён статус для заказа на сумму", invoice_sum,
                                      "с номером накладной", invoice_num)
                                deliver.status_id = self.ord_deliv_pay_rec_spsr.pk
                                deliver.save()
                            else:
                                print("Изменения уже внесены")

    def remove_xls_files(self, *args, **options):
        for file in self.files:
            os.remove(file)