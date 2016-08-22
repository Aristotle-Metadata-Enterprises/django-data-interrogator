from django.apps import AppConfig


class ShopConfig(AppConfig):
    name = 'shop'

    def ready(self):
        from .functions import NotEqual  # NOQA - trigger registration
