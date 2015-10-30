from django.conf.urls import patterns, url

urlpatterns = patterns('data_interrogator.views',
    #url(r'^room/$', 'data_interrogator.views.custom_table', name='custom_table'),
    url(r'^upload/$', 'admin_upload', name='admin_upload'),
)
