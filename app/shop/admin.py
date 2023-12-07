from django.contrib import admin
from shop import models

admin.site.register(models.Product)
admin.site.register(models.ProductTag)
admin.site.register(models.Branch)
admin.site.register(models.SalesPerson)
admin.site.register(models.Sale)
