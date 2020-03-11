from data_interrogator import views
from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.conf.urls.static import static
# urls.py

#app_name = 'data_interrogator'
urlpatterns = [
    path(r'', views.InterrogationView.as_view(template_name="base.html"), name='datatablepage'),
    path(r'typeahead/', views.InterrogationView.as_view(template_name="typeahead.html")),
    path(r'admin/', include("data_interrogator.admin_urls")),
    path(r'admin/', admin.site.urls),
    path(r'data/', include("data_interrogator.urls")),
    # path(r'product_reports', views.InterrogationView.as_view(
    # 	report_models=[("shop","Product")],
    # 	allowed=[("shop","Product")],
    # 	template_name="typeahead.html"
    # )),
    path(r'product_reports', include(views.InterrogationAutocompleteUrls(
    	report_models=[("shop","Product")],
    	allowed=[("shop","Product")],
    	template_name="typeahead.html"
    ).urls)),
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
