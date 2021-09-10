from django.apps import apps
from decimal import Decimal
from django.db.models import Case, Sum, When, F, ExpressionWrapper
from django.db.models import Count
from django.db.models.fields import DecimalField
from django.test import TestCase
from django.utils.encoding import smart_text
from django.utils.http import urlencode
from data_interrogator.interrogators import Interrogator, Allowable


class TestInterrogatorPages(TestCase):
    """NB: these tests use the url configuration specified by the shop display app"""
    fixtures = ['data.json']

    def test_page_room(self):
        """Test that the interrogator page for sales people returns the correct results"""

        params_dict = {
            'lead_base_model': 'shop:salesperson',
            'filter_by': '',
            'columns': 'name|sum(sale.sale_price - sale.product.cost_price)|',
            'sort_by': '',
            'action': ''
        }
        url = '/full_report/?' + urlencode(params_dict)
        response = self.client.get(url)

        page = smart_text(response.content)
        self.assertEqual(response.status_code, 200)
        SalesPerson = apps.get_model('shop', 'SalesPerson')

        # Assert that the sales people are appearing in the data interrogator view
        salespeople = SalesPerson.objects.order_by('name').values("name").annotate(
            total=Sum(
                ExpressionWrapper(
                    F('sale__sale_price') - F('sale__product__cost_price'),
                    output_field=DecimalField()
                ), 
                output_field=DecimalField(),
                distinct=False
                ),
        )

        for row in salespeople:
            self.assertTrue(str(row['name']) in page)
            self.assertTrue(str(row['total']) in page)

    def test_page_sumif(self):
        """Test that the data interrogators sum if works"""
        params_dict = {
            'lead_base_model': 'shop:product',
            'filter_by': '',
            'columns': 'name'
                       '|sale.seller.name'
                       '|sumif(sale.sale_price, sale.state.iexact=NSW)'
                       '|sumif(sale.sale_price, sale.state.iexact=VIC)'
        }
        url = '/full_report/?' + urlencode(params_dict)
        response = self.client.get(url)

        page = smart_text(response.content)
        self.assertEqual(response.status_code, 200)

        # Assert that the SumIf in the data interrogator works the same way to Case in the Django ORM
        Product = apps.get_model('shop', 'Product')

        q = Product.objects.order_by('name').values("name", "sale__seller__name").annotate(
            vic_sales=Sum(
                Case(
                    When(
                        sale__state__iexact='VIC', then=F('sale__sale_price')
                        ),
                        output_field=DecimalField(), 
                        default=0.0,
                        ),
            ),
            nsw_sales=Sum(
                Case(
                    When(
                        sale__state__iexact='NSW', then=F('sale__sale_price')
                        ), 
                        default=0.0,
                        output_field=DecimalField(),
                        )
            )
        )
        for row in q:
            self.assertTrue(str(row['name'] in page))
            self.assertTrue(str(row['vic_sales']) in page)
            self.assertTrue(str(row['nsw_sales']) in page)


class TestInterrogators(TestCase):
    fixtures = ['data.json',]

    def assertIterablesEqual(self, list_a, list_b):
        for a, b in zip(list_a, list_b):
            self.assertEqual(a, b)
        self.assertEqual(len(list_a), len(list_b))

    def test_sumif(self):
        Product = apps.get_model('shop', 'Product')

        report = Interrogator(
            report_models=[('shop','Product'),],
            allowed=Allowable.ALL_MODELS,
            excluded=[]
        )

        results = report.interrogate(
            base_model='shop:Product',
            columns=['name','vic_sales:=sumif(sale.sale_price, sale.state.iexact=VIC)'],
            filters=[]
        )
        
        q = Product.objects.order_by('name').values("name").annotate(
            vic_sales=Sum(
                Case(
                    When(
                        sale__state__iexact='VIC',
                        then=F('sale__sale_price'),
                    ),
                    default=0.0,
                    output_field=DecimalField()
                )
            )
            )
        self.assertTrue(results['count'] == q.count())
        self.assertEqual(results['rows'], list(q))

    def test_cannot_join_forbidden_model(self):
        SalesPerson = apps.get_model('shop', 'SalesPerson')
        report = Interrogator(
            report_models=[('shop','Sale'),],
            allowed=Allowable.ALL_MODELS,
            excluded=[('shop','SalesPerson')]
        )
        self.assertTrue(report.is_excluded_model(SalesPerson))

        results = report.interrogate(
            base_model='shop:Sale',
            columns=['product__name', 'seller__name'],
            filters=[]
        )
        self.assertEqual(len(results['errors']), 1)
        self.assertEqual(
            results['errors'][0],
            'Joining tables with the column [seller__name] is forbidden, this column is removed from the output.'
        )

    def test_cannot_join_forbidden_app(self):
        SalesPerson = apps.get_model('shop', 'SalesPerson')
        report = Interrogator(
            report_models=[('shop','Sale'),],
            allowed=Allowable.ALL_MODELS,
            excluded=[('shop')]
        )
        self.assertTrue(report.is_excluded_model(SalesPerson))

        results = report.interrogate(
            base_model='shop:Sale',
            columns=['seller__name'],
            filters=[]
        )
        self.assertEqual(len(results['errors']), 1)
        self.assertEqual(
            results['errors'][0],
            'Joining tables with the column [seller__name] is forbidden, this column is removed from the output.'
        )

    def test_interrogator_cannot_start_from_forbidden_model(self):
        """Test that a forbidden model cannot be the base model in the interrogator"""
        SalesPerson = apps.get_model('shop', 'SalesPerson')

        report = Interrogator(
            report_models=[('shop', 'Sale')],
            allowed=Allowable.ALL_MODELS,
            excluded=[('shop', 'SalesPerson')]
        )

        results = report.interrogate(
            base_model='shop:SalesPerson',
            columns=['seller__name'],
            filters=[]
        )

        self.assertIn('Something went wrong - ModelNotAllowedException', results['errors'][0])

    def test_interrogator(self):
        SalesPerson = apps.get_model('shop', 'SalesPerson')

        report = Interrogator(
            report_models=[('shop','SalesPerson'),],
            allowed=Allowable.ALL_MODELS,
            excluded=[]
        )

        results = report.interrogate(
            base_model='shop:SalesPerson',
            columns=['name','num:=count(sale)'],
            filters=[]
        )
        q = SalesPerson.objects.order_by('name').values("name").annotate(num=Count('sale')) #.filter(num__gt=0) #.distinct()
        self.assertTrue(results['count'] == q.count())
        self.assertEqual(results['rows'], list(q))

    def test_interrogator_with_sum_and_math(self):
        SalesPerson = apps.get_model('shop', 'SalesPerson')
        unique_names = SalesPerson.objects.values("name").distinct()

        report = Interrogator(
            report_models=[('shop','SalesPerson'),],
            allowed=Allowable.ALL_MODELS,
            excluded=[]
        )

        results = report.interrogate(
            'shop:SalesPerson',
            columns=['name','profit:=sum(sale.sale_price - sale.product.cost_price)','total:=count(sale)'],
        )
        q = SalesPerson.objects.order_by('name').values("name").annotate(
            total=Count('sale'),
            profit=Sum(F('sale__sale_price') - F('sale__product__cost_price'), output_field=DecimalField())
        )
        for r in results['rows']:
            print("| {: <16} \t| {} | {} |".format(*r.values()))
        self.assertTrue(results['count'] == q.count())
        self.assertEqual(results['rows'], list(q))
        self.assertTrue(results['count'] == unique_names.count())

        results = report.interrogate(
            'shop:SalesPerson',
            columns=['name','profit:=sum(sale.sale_price - sale.product.cost_price)','total:=count(sale)'],
            filters=['name = Jody Wiffle']
        )
        q = SalesPerson.objects.order_by('name').values("name").annotate(
            total=Count('sale'),
            profit=Sum(F('sale__sale_price') - F('sale__product__cost_price'))
        ).filter(name='Jody Wiffle')
        self.assertTrue(results['count'] == q.count())
        self.assertEqual(results['rows'], list(q))
        self.assertTrue(results['count'] == unique_names.filter(name='Jody Wiffle').count())

        results = report.interrogate(
            'shop:SalesPerson',
            columns=['name','profit:=sum(sale.sale_price - sale.product.cost_price)','total:=count(sale)'],
            filters=['name.icontains = Wiffle']
        )
        q = SalesPerson.objects.order_by('name').values("name").annotate(
            total=Count('sale'),
            profit=Sum(F('sale__sale_price') - F('sale__product__cost_price'))
        ).filter(name__icontains='Wiffle')
        self.assertTrue(results['count'] == q.count())
        self.assertEqual(results['rows'], list(q))
        self.assertTrue(results['count'] == unique_names.filter(name__icontains='Wiffle').count())

    def test_not_equal(self):
        """Test not equal filter is working"""
        Product = apps.get_model('shop', 'Product')

        excluded = Product.objects.create(name="EXCLUDED", category=Product.WOMEN, cost_price=Decimal('10.00'))
        Product.objects.create(name="INCLUDED_1", category=Product.WOMEN, cost_price=Decimal('3.00'))
        Product.objects.create(name="INCLUDED_2", category=Product.WOMEN, cost_price=Decimal('25.00'))

        self.assertNotIn(
            excluded,
            Product.objects.filter(name__ne="EXCLUDED").order_by('name')
        )
