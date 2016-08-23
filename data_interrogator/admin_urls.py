from django.conf.urls import url
from django.views.generic import TemplateView
from data_interrogator import views


urlpatterns = [
    url(r'^data_interrogator/analytics/$', views.AdminInterrogationRoom.as_view(), name='admin_analytics'),
    url(r'^data_interrogator/pivot/$', views.AdminPivotTable.as_view(), name='admin_pivot_table'),
    url(r'^data_interrogator/upload/$', views.admin_upload, name='admin_upload'),
]
