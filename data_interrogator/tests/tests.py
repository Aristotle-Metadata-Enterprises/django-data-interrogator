from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.utils import setup_test_environment

setup_test_environment()

class LoadSomePages(TestCase):
    fixtures = ['data.json',]
    
    def test_room(self):
        response = self.client.get("/data/room/")
        self.assertEqual(response.status_code, 200)
    def test_pivot(self):
        response = self.client.get("/data/pivot/")
        self.assertEqual(response.status_code, 200)

    def test_room(self):
        response = self.client.get("/data/room/?lead_suspect=shop%3ASalesPerson&filter_by=&filter_by=&columns=name&columns=sum%28sale.sale_price+-+sale.product.cost_price%29&columns=count%28sale%29&sort_by=")
        self.assertEqual(response.status_code, 200)
        self.assertTrue('| Jody Wiffle | 1289.0 | 136 |' in response.content)

    def test_pivot(self):
        response = self.client.get("/data/pivot/?lead_suspect=shop%3AProduct&filter_by=&filter_by=&column_1=sale.state&column_2=name&aggregators=profit%3Dsum%28sale.sale_price+-+cost_price%29")
        self.assertEqual(response.status_code, 200)
        self.assertTrue('| Beanie ||  119,  profit:1314 |  17,  profit:190 |  41,  profit:367 |  31,  profit:371 |  98,  profit:1050 |  11,  profit:122 |' in response.content)
