from data_interrogator import views
from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.contrib import admin

#app_name = 'data_interrogator'
urlpatterns = [
    url(r'^$', views.InterrogationRoom.as_view(template_name="base.html"), name='datatablepage'),
    url(r'^admin/', include("data_interrogator.admin_urls")),
    #url(r'^admin/', include(admin.site.urls)),
    url(r'^data/', include("data_interrogator.urls")),

]
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
