from django.db import models


class Product(models.Model):
    verbose_name = "Product for Sale"
    interrogator_name = "Products"
    KIDS = 'Kids'
    MEN = 'Men'
    WOMEN = 'Women'

    categories = (
        (KIDS, KIDS), (MEN, MEN), (WOMEN, WOMEN)
    )

    name = models.CharField(max_length=50)
    category = models.CharField(max_length=10, choices=categories, db_index=True)
    cost_price = models.DecimalField(max_digits=7, decimal_places=2)

    def __str__(self):
        return self.name


class ProductTag(models.Model):
    name = models.CharField(max_length=50)
    data = models.TextField()
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.product.name}: {self.name}: {self.data}"


class Branch(models.Model):
    verbose_name = "Sales Branch"
    VIC = 'VIC'
    NSW = 'NSW'
    QLD = 'QLD'
    TAS = 'TAS'
    SA = 'SA'
    WA = 'WA'
    states = (
        (VIC, VIC), (NSW, NSW), (QLD, QLD),
        (TAS, TAS), (SA, SA), (WA, WA)
    )

    name = models.CharField(max_length=50)
    state = models.CharField(max_length=3, choices=states)


class SalesPerson(models.Model):
    name = models.CharField(max_length=50)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    age = models.IntegerField()


class Sale(models.Model):
    verbose_name = "Sale"
    VIC = 'VIC'
    NSW = 'NSW'
    QLD = 'QLD'
    TAS = 'TAS'
    SA = 'SA'
    WA = 'WA'
    states = (
        (VIC, VIC), (NSW, NSW), (QLD, QLD),
        (TAS, TAS), (SA, SA), (WA, WA)
    )

    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    seller = models.ForeignKey(SalesPerson, on_delete=models.CASCADE)
    sale_date = models.DateTimeField()
    sale_price = models.DecimalField(max_digits=7, decimal_places=2)
    state = models.CharField(max_length=3, choices=states)

    def __str__(self):
        return "<{0}>: {1}".format(self.pk, self.sale_price)
