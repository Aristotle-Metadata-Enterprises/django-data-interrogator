from django.conf.urls import url
from . import views

app_name = 'data_interrogator'
urlpatterns = [
    url(r'^room/$', views.custom_table, name='custom_table'),
    url(r'^table(?P<url>/.*/)?$', views.datatable, name='datatablepage'),
    url(r'^pivot/$', views.pivot_table, name='pivot'),
    url(
        r'^ac-field/$',
        views.lookups.FieldLookupTypeahead.as_view(),
        name='field-lookup-autocomplete',
    ),
]
