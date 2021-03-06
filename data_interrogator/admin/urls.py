from django.urls import path, include

from data_interrogator.admin import views

urlpatterns = [
    # url(r'^data_interrogator/analytics/$', views.AdminInterrogationRoom.as_view(), name='admin_analytics'),
    # url(r'^data_interrogator/pivot/$', views.AdminPivotTable.as_view(), name='admin_pivot_table'),
    path(r'data_interrogator/pivot/', views.AdminInterrogationRoom.as_view(), name='admin_analytics_pivot'),
    path(r'data_interrogator/analytics/', include(views.AdminInterrogationAutocompleteUrls(
        # template_name="admin/analytics/analytics.html",
        path_name="admin_analytics"
    ).urls)),
]
