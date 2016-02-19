from django.conf.urls import patterns, url

urlpatterns = patterns('data_interrogator.views',
    #url(r'^room/$', 'data_interrogator.views.custom_table', name='custom_table'),
    url(r'^column_generator/$', 'column_generator', name='column_generator'),
    url(r'^table(?P<url>/.*/)?$', 'datatable', name='datatable'),
    url(r'^pivot/$', 'pivot_table', name='pivot'),
)
