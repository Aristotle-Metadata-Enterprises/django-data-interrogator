from datetime import datetime
from decimal import Decimal
from django.db.models import Q
from django.test import TestCase
from django.utils import timezone

from .functions import SumIf, TruncQtr, TruncQuarter, qtr_over_qtr_revenue
from .models import Product, Sale


class ShopTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        # we don't want data created by data migrations
        Product.objects.all().delete()

    def test_smoketest(self):
        self.assertTrue(True)

    def test_notequal(self):
        Product.objects.create(name='EXCL', category=Product.WOMEN, cost_price=Decimal('10.00'))
        Product.objects.create(name='INCL_A', category=Product.WOMEN, cost_price=Decimal('3.00'))
        Product.objects.create(name='INCL_B', category=Product.WOMEN, cost_price=Decimal('6.00'))

        self.assertQuerysetEqual(
            Product.objects.filter(name__ne='EXCL').order_by('name'), [
                ('INCL_A', Product.WOMEN), ('INCL_B', Product.WOMEN),
            ], lambda p: (p.name, p.category)
        )

    def test_sumif_condition(self):
        Product.objects.create(name='EXCL', category=Product.WOMEN, cost_price=Decimal('10.00'))
        Product.objects.create(name='INCL_A', category=Product.WOMEN, cost_price=Decimal('3.00'))
        Product.objects.create(name='INCL_B', category=Product.WOMEN, cost_price=Decimal('6.00'))

        qs = Product.objects.filter(category=Product.WOMEN).values('category').annotate(
            total=SumIf('cost_price', name__startswith='INCL')
        )
        self.assertQuerysetEqual(qs, [
                {"category": Product.WOMEN, "total": Decimal('9.00')}
            ], lambda o: o
        )

    def test_sumif_qlookup(self):
        Product.objects.create(name='EXCL', category=Product.WOMEN, cost_price=Decimal('10.00'))
        Product.objects.create(name='INCL_A', category=Product.WOMEN, cost_price=Decimal('3.00'))
        Product.objects.create(name='INCL_B', category=Product.WOMEN, cost_price=Decimal('6.00'))

        qs = Product.objects.filter(category=Product.WOMEN).values('category').annotate(
            total=SumIf('cost_price', Q(name__startswith='INCL'))
        )
        self.assertQuerysetEqual(qs, [
                {"category": Product.WOMEN, "total": Decimal('9.00')}
            ], lambda o: o
        )

    def test_quarter_trunc(self):
        p1 = Product.objects.create(name='INCL_A', category=Product.WOMEN, cost_price=Decimal('3.00'))
        sale_date = datetime(2016, 8, 12, tzinfo=timezone.utc)
        quarter = datetime(2016, 7, 1, tzinfo=timezone.utc)
        Sale.objects.create(product=p1, sale_date=sale_date, sale_price=Decimal('4.00'), state=Sale.VIC)

        self.assertQuerysetEqual(Sale.objects.annotate(quarter=TruncQuarter('sale_date')), [
                quarter,
            ], lambda s: s.quarter
        )

    def test_qtr_trunc(self):
        p1 = Product.objects.create(name='INCL_A', category=Product.WOMEN, cost_price=Decimal('3.00'))
        sale_date = datetime(2016, 8, 12, tzinfo=timezone.utc)
        quarter = datetime(2016, 7, 1, tzinfo=timezone.utc)
        Sale.objects.create(product=p1, sale_date=sale_date, sale_price=Decimal('4.00'), state=Sale.VIC)

        self.assertQuerysetEqual(Sale.objects.annotate(quarter=TruncQtr('sale_date')), [
                quarter,
            ], lambda s: s.quarter
        )

    def test_cursor(self):
        p1 = Product.objects.create(name='INCL_A', category=Product.WOMEN, cost_price=Decimal('2.00'))
        sd1 = datetime(2016, 1, 1, tzinfo=timezone.utc)
        sd2 = datetime(2016, 4, 1, tzinfo=timezone.utc)
        sd3 = datetime(2016, 4, 3, tzinfo=timezone.utc)
        Sale.objects.create(product=p1, sale_date=sd1, sale_price=Decimal('4.00'), state=Sale.VIC)
        Sale.objects.create(product=p1, sale_date=sd2, sale_price=Decimal('4.00'), state=Sale.VIC)
        Sale.objects.create(product=p1, sale_date=sd3, sale_price=Decimal('4.00'), state=Sale.VIC)

        # forgive me.
        class List(list):
            pass
        results = List(qtr_over_qtr_revenue())
        results.ordered = True
        
        self.assertQuerysetEqual(
            results, [
                (sd1, Decimal('4.00'), None),
                (sd2, Decimal('8.00'), '100.00%'),
            ], lambda r: (r['quarter'], r['revenue'], r['rgrowth'])
        )
