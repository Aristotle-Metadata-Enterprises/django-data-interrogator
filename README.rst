django-data-interrogator
========================

``django-data-interrogator`` is a plug in table builder that allows users to easily interrogate information from a django database. In essence it provides a smart and sane frontend for building tabular data from the django database queryset API - specifically ``values``, ``filter``, ``order_by`` and a handful of annotations.

Installing
----------

Add the *Data Interrogator* to your ``INSTALLED_APPS``::

   INSTALLED_APPS = (
     #...
     'data_interrogator',
   )

Quickstart
----------

#. Make a list of suspects (models you wish to interrogate) and enter models into *witness protection* (models you want to disallow access to)::

    DATA_INTERROGATION_DOSSIER = {
        'suspects': [
            {'model':("yourapplabel","YourModelName")},
            {'model':("yourapplabel","YourOtherModelName")},
         ],
        'witness_protection' : ["User","Revision","Version"]
    }

   Notes: ``suspects`` are used to query the django ``ContentType`` database. The values in ``witness_protection`` are matched against columns that might be returned, and any columns that match will be dropped from output.

#. Make a view to capture form requests and pass the request off to the *interrogator*::

    def custom_table(request):
        data = interrogation_room(request)
        return render(request, 'your/interrogation/template.html', data)

#. Make sure your template can handle the interrogation procedures::

    {% load data_interrogator %}

    {% lineup %} {# loads the form for selecting columns #}
    {% interrogation_room %} {# loads the table where data is displayed #}
    
#. Thats it!

Extra dossier configuration
---------------------------

The *Interrogation dossier* is a powerful way of altering how data is output. Along with specifying a model that can be a suspect, you can specify ``wrapsheets`` for them - i.e. special ways of displaying columns.

Below is an example dossier for a single model, with a wrapsheet for the column ``foo`` on the model ``YourModel``::

    DATA_INTERROGATION_DOSSIER = {
        'suspects': [
          { "model":("yourappname","YourModel"),
            "wrap_sheets": {
                "foo": {
                    "columns": ['pk','bar'],
                    "template": "yourapp/special_columns/for_foo.html",
                }
           },
        ]
     }

The ``columns`` value in the ``wrapsheet`` specified additional columns of data to be retrieved when querying the specified attribute. So in the above example, whenever anyone requests the ``foo`` attribute when interrogating the ``YourModel`` model the ``pk`` and ``bar`` fields will also be retrieved, *but will not be visible in the output table*. However they will be accessible in the ``yourapp/special_columns/for_foo.html`` template which will be used when rendering the ``<td>`` table cell in the table.