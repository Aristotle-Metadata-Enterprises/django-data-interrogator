from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic.base import TemplateView

from data_interrogator import views
from data_interrogator.views.views import InterrogationAPIAutocompleteUrls

from data_interrogator.interrogators import Allowable


def allow_all_users():
    return True


urlpatterns = [
    path(r'', TemplateView.as_view(template_name="home.html")),
    path(r'', views.InterrogationView.as_view(template_name="base.html"), name='datatablepage'),
    path(r'typeahead/', views.InterrogationView.as_view(template_name="typeahead.html")),
    path(r'admin/', include("data_interrogator.admin.urls")),
    path(r'admin/', admin.site.urls),
    path(r'api/product_report/', include(InterrogationAPIAutocompleteUrls(
        report_models=[("shop", "Product")],
        allowed=[("shop")],
        excluded=[("shop", "SalesPerson")],
        test_func=allow_all_users
    ).urls)),
    path(r'product_report/', include(views.InterrogationAutocompleteUrls(
        report_models=[("shop", "Product"), ("shop", "Branch")],
        allowed=[("shop")],
        excluded=[("shop", "SalesPerson")],
        template_name="typeahead.html",
        test_func=allow_all_users
    ).urls)),
    path(r'shop_report/', include(views.InterrogationAutocompleteUrls(
        report_models=[("shop",)],
        allowed=[("shop",)],
        template_name="typeahead.html",
        test_func=allow_all_users
    ).urls)),
    path(r'full_report/', include(views.InterrogationAutocompleteUrls(
        report_models=Allowable.ALL_MODELS,
        allowed=Allowable.ALL_MODELS,
        excluded=[],
        template_name="typeahead.html",
        test_func=allow_all_users
    ).urls)),
]
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
