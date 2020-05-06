from django.contrib.auth.decorators import user_passes_test
from django.utils.decorators import method_decorator

from data_interrogator.admin.forms import AdminInvestigationForm, AdminPivotTableForm
from data_interrogator.interrogators import Allowable
from data_interrogator.views import InterrogationView, InterrogationAutocompleteUrls, PivotTableView, \
    InterrogationAutoComplete


class AdminInterrogationRoom(InterrogationView):
    template_name = 'admin/analytics/analytics.html'
    form_class = AdminInvestigationForm

    report_models = Allowable.ALL_MODELS
    allowed = Allowable.ALL_APPS
    excluded = []

    @method_decorator(user_passes_test(lambda u: u.is_superuser))
    def get(self, request):
        return super(AdminInterrogationRoom,self).get(request)


class AdminInterrogationAutocompleteUrls(InterrogationAutocompleteUrls):
    interrogator_view_class = AdminInterrogationRoom
    interrogator_autocomplete_class = InterrogationAutoComplete


class AdminPivotTableView(PivotTableView):
    form_class = AdminPivotTableForm
    template_name = 'admin/analytics/pivot.html'
