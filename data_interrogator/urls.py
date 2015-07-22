from django.conf.urls import patterns, include, url
from django.contrib import admin

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'data_interrogator.views.home', name='home'),

    #url(r'^/', include(admin.site.urls)),
    url(r'^room/$', 'data_interrogator.views.custom_table', name='custom_table'),
)
