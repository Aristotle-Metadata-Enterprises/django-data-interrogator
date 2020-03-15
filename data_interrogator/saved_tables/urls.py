from django.conf.urls import url
from . import views

app_name = 'data_interrogator'
urlpatterns = [
    url(r'^table(?P<url>/.*/)?$', views.datatable, name='datatablepage'),
    url(r'^pivot/$', views.pivot_table, name='pivot'),
    url(
        r'^ac-field/$',
        views.lookups.FieldLookupTypeahead.as_view(),
        name='field-lookup-autocomplete',
    ),
]
