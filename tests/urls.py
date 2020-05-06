from django.urls import include, path
from data_interrogator import views
from data_interrogator.interrogators import Allowable

urlpatterns = [
    path(r'data/', include(views.InterrogationAutocompleteUrls(
        report_models=Allowable.ALL_MODELS,
        allowed=Allowable.ALL_MODELS,
        excluded=[],
        template_name="test_table_display.html"
    ).urls)),
]
