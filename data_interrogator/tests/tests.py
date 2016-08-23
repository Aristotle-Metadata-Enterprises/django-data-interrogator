from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.utils import setup_test_environment

setup_test_environment()

class TestInterrogators(TestCase):
    fixtures = ['data.json',]
    
    def test_page_room(self):
        response = self.client.get("/data/room/?lead_suspect=shop%3ASalesPerson&filter_by=&filter_by=&columns=name&columns=sum%28sale.sale_price+-+sale.product.cost_price%29&columns=count%28sale%29&sort_by=")
        self.assertEqual(response.status_code, 200)
        self.assertTrue('| Jody Wiffle | 1289.0 | 136 |' in response.content)

    def test_page_pivot(self):
        response = self.client.get("/data/pivot/?lead_suspect=shop%3AProduct&filter_by=&filter_by=&column_1=sale.state&column_2=name&aggregators=profit%3Dsum%28sale.sale_price+-+cost_price%29")
        self.assertEqual(response.status_code, 200)

        self.assertTrue('| Beanie ||' in response.content)
        beanie_values = [line for line in response.content.split('\n') if line.startswith('| Beanie ||')]
        self.assertTrue(len(beanie_values) == 1)

        beanie_values = [v.strip() for v in beanie_values[0].strip().split('|| ',1)[1].split(' | ')]

        header = [line for line in response.content.split('\n') if line.startswith("| Header |")][0]
        header = header.strip().split('|| ',1)[1].split(' | ')

        expected_states = "NSW | SA | QLD | TAS | VIC | WA".split(" | ")
        expected_values = "  119,  profit:1314 |  17,  profit:190 |  41,  profit:367 |  31,  profit:371 |  98,  profit:1050 |  11,  profit:122  "
        expected_values = [v.strip() for v in expected_values.split("|")]
        expected = dict(zip(expected_states,expected_values))

        for state,val in zip(header, beanie_values):
            self.assertTrue(expected[state] == val)

    def test_page_sumif(self):
        response = self.client.get("/data/room/?lead_suspect=shop%3AProduct&filter_by=name%3DWinter+Coat&filter_by=&columns=name&columns=Salesperson%3A%3Dsale.seller.name&columns=NSW+sales%3A%3Dsumif%28sale.sale_price%2C+sale.state.iexact%3DNSW%29&columns=VIC+sales%3A%3Dsumif%28sale.sale_price%2C+sale.state.iexact%3DVIC%29")
        self.assertEqual(response.status_code, 200)
        self.assertTrue('| name | Salesperson | NSW sales | VIC sales |' in response.content)
        self.assertTrue('| Winter Coat | Morty Smith | 1605.00 | 1782.00 |' in response.content)

        response = self.client.get("/data/room/?lead_suspect=shop%3AProduct&filter_by=name%3DWinter+Coat&filter_by=sale.state.iexact%3DVIC&filter_by=&columns=name&columns=sale.seller.name&columns=sum%28sale.sale_price%29")
        self.assertEqual(response.status_code, 200)
        self.assertTrue('| Winter Coat | Morty Smith | 1782.00 |' in response.content)

        response = self.client.get("/data/room/?lead_suspect=shop%3AProduct&filter_by=name%3DWinter+Coat&filter_by=sale.state.iexact%3DNSW&filter_by=&columns=name&columns=sale.seller.name&columns=sum%28sale.sale_price%29")
        self.assertEqual(response.status_code, 200)
        self.assertTrue('| Winter Coat | Morty Smith | 1605.00 |' in response.content)

    def test_interrogator(self):
        from data_interrogator.views import Interrogator

        from django.apps import apps
        SalesPerson = apps.get_model('shop', 'SalesPerson')

        inter = Interrogator(
            'shop:SalesPerson',
            columns=['name','sum(sale.sale_price - sale.product.cost_price)','count(sale)'],
            filters=[]
        ).interrogate()
        q = SalesPerson.objects.filter(sale__sale_price__gt=0).distinct()
        self.assertTrue(inter['count'] == q.count())

        inter = Interrogator(
            'shop:SalesPerson',
            columns=['name','sum(sale.sale_price - sale.product.cost_price)','count(sale)'],
            filters=['name = Jody Wiffle']
        ).interrogate()
        self.assertTrue(inter['count'] == SalesPerson.objects.filter(name='Jody Wiffle').count())

        inter = Interrogator(
            'shop:SalesPerson',
            columns=['name','sum(sale.sale_price - sale.product.cost_price)','count(sale)'],
            filters=['name.icontains = Wiffle']
        ).interrogate()
        self.assertTrue(inter['count'] == SalesPerson.objects.filter(name__icontains='Wiffle').count())

        inter = Interrogator(
            'shop:SalesPerson',
            columns=['name','total profit:= sum(sale.sale_price - sale.product.cost_price)','count(sale)'],
            filters=[]
        ).interrogate()
        
        self.assertTrue('total profit' in inter['columns'])
        self.assertFalse(any(['sum(sale.sale_price' in header for header in inter['columns']]))
        
