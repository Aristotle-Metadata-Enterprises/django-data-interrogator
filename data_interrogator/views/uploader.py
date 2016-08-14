from django.contrib.auth.decorators import user_passes_test
from django.core import exceptions
from django.core.management import call_command
from django.core.urlresolvers import reverse
from django.db.models import F, Count, Min, Max, Sum, Value, Avg, ExpressionWrapper, DurationField, FloatField, CharField
from django.db.models import functions as func
from django.http import JsonResponse, QueryDict
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import get_template

import tempfile, os

from datetime import timedelta

from data_interrogator import forms

@user_passes_test(lambda u: u.is_superuser)
def admin_upload(request):

    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = forms.UploaderForm(request.POST, request.FILES)
        # check whether it's valid:
        if form.is_valid():
            # process the data in form.cleaned_data as required
            # ...
            # redirect to a new URL:
            opts = {}
            if form.cleaned_data['separator'] == 'comma':
                opts['separator'] = ','
            elif form.cleaned_data['separator'] == 'tab':
                opts['separator'] = 'tab'
            else:
                opts['separator'] = form.cleaned_data['other_separator']
                
            opts['model_name'] = form.cleaned_data['main_model']
            opts['update_keys'] = form.cleaned_data['update_keys']
            
            ### get the inmemory file
            data = request.FILES.get('data_file') # get the file from the curl
            
            ### write the data to a temp file
            tup = tempfile.mkstemp() # make a tmp file
            f = os.fdopen(tup[0], 'w') # open the tmp file for writing
            f.write(data.read()) # write the tmp file
            f.close()
            
            ### return the path of the file
            filepath = tup[1] # get the filepath

            from StringIO import StringIO
            stderr = StringIO()
            stdout = StringIO()
            output = call_command('dragnet', filepath, verbosity=3, interactive=False, stdout=stdout,stderr=stderr, **opts)
            stderr.seek(0)
            stdout.seek(0)
            context = {'output':stdout.read(),'errs':stderr.read()}
            return render(request, "data_interrogator/admin/upload_done.html", context)

    # if a GET (or any other method) we'll create a blank form
    else:
        form = forms.UploaderForm()
        
    data = {'form':form}
    

    return render(request, "data_interrogator/admin/upload.html", data)
