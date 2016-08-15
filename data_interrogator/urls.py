from django.conf.urls import url
from . import views

urlpatterns = [
    #url(r'^room/$', 'data_interrogator.views.custom_table', name='custom_table'),
    url(r'^column_generator/$', views.column_generator, name='column_generator'),
    url(r'^table(?P<url>/.*/)?$', views.datatable, name='datatablepage'),
    url(r'^pivot/$', views.pivot_table, name='pivot'),
]
