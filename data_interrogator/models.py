from django.db import models
from django.conf import settings
#from django.contrib.flatpages.models import FlatPage
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from model_utils import Choices

suspects = getattr(settings, 'DATA_INTERROGATION_DOSSIER', {}).get('suspects',[])

class DataTablePage(models.Model):
    """
    This is a semi-re-write of the Django FlatPages app as site configs are superfluous and we need extra fields.
    We also probably don't want comments.
    """
    url = models.CharField(_('URL'), max_length=100, db_index=True,primary_key=True)
    title = models.CharField(_('title'), max_length=200)
    content = models.TextField(_('content'), blank=True)

    STATUS = Choices(('draft','Draft'),('published','Published'))
    status = models.CharField(choices=STATUS, default=STATUS.draft, max_length=20,
        help_text=_("Draft items will only be seen by super users, published items can be seen by those allowed by the registration required field."))
    registration_required = models.BooleanField(_('registration required'),
        help_text=_("If this is checked, only logged-in users will be able to view the page."),
        default=False)
    template_name = models.CharField(_('template name'), max_length=70, blank=True,
        help_text=_(
            "Example: 'exampleapp/contact_page.html'. If this isn't provided, "
            "the system will use 'data_interrogator/by_the_book.html'."
        ),
    )

    SUSPECTS = Choices(*[
        ("%s:%s"%tuple(suspect['model']),suspect['model'][1]) for suspect in suspects
        ])
    base_model = models.CharField(choices=SUSPECTS, max_length=100)

    class Meta:
        ordering = ('url',)

    def __str__(self):
        return "%s - %s" % (self.url, self.title)

    def get_absolute_url(self):
        return reverse('data_interrogator:datatable', kwargs={'url': self.url})
            
class DataTablePageColumn(models.Model):
    table = models.ForeignKey(DataTablePage,related_name="columns")
    header_text = models.CharField(max_length=255,null=True,blank=True,
        help_text="The text displayed in the table header for this column")
    column_definition = models.TextField(
        help_text="The definition used to extract data from the database")
    def __repr__(self):
        return self.column_definition

class DataTablePageFilter(models.Model):
    table = models.ForeignKey(DataTablePage,related_name="filters")
    filter_definition = models.TextField(
        help_text="The definition used to extract data from the database")
    def __repr__(self):
        return self.filter_definition

class DataTablePageOrder(models.Model):
    table = models.ForeignKey(DataTablePage,related_name="order")
    ordering = models.TextField()
    def __repr__(self):
        return self.ordering
