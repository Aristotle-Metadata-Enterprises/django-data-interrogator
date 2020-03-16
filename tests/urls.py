from django.urls import include, path
from data_interrogator import views
from data_interrogator.interrogators import allowable

urlpatterns = [
    path(r'data/', include(views.InterrogationAutocompleteUrls(
        report_models=allowable.ALL_MODELS,
        allowed=allowable.ALL_MODELS,
        excluded=[],
        template_name="test_table_display.html"
    ).urls)),
]
