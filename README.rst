django-data-interrogator
========================

``django-data-interrogator`` is a plug in table builder that allows users to easily interrogate information from a django database. In essence it provides a smart and sane frontend for building tabular data from the django database queryset API - specifically ``values``, ``filter``, ``order_by`` and a handful of annotations.

.. contents::

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

Bootstrap your way to a nicer interrogation room
------------------------------------------------

*Data Interrogator* integrates nicely with `Bootstrap <http://getbootstrap.com>`_ and by default adds a ``table`` class `to use Bootstrap's built in styling for tables <http://getbootstrap.com/css/#tables>`_. If you want to do additional customisation of the "interrogation room" table, just override the ``data_interrogator/interrogation_room.html`` template. For example to convert the interrogation room table into one that is responsive and has table striping, just change the template to that below::

    <table class="table table-responsive table-striped">
        <thead>
            <tr>
                {% for col in columns %}
                    <th data-switchable='true' data-sortable='true'>{% clean_column_name col %}</th>
                {% endfor %}
            </tr>
        </thead>
        <tbody>
            {% for row in rows %}
            <tr>
                {% for col in columns %}
                    <td>{% wrap_sheet row col %}</td>
                {% endfor %}
            </tr>
            {% endfor %}
        </tbody>
    </table>

Styling the data line-up
~~~~~~~~~~~~~~~~~~~~~~~~
The data line-up is the form used to select models, columns and contstaints, this doesn't come with built-in support for Bootstrap, but can be overriden in a similar way to the example above by overriding the ``data_interrogator/lineup.html`` template.

Adding Bootstrap-Table for even more powerful investigations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
`Bootstrap-Table <https://github.com/wenzhixin/bootstrap-table>`_ is a powerful front-end table manipulation plug-in for Bootstrap that providings additional filtering, sorting and searching within html tables. `It also has an export extension <http://bootstrap-table.wenzhixin.net.cn/extensions/#table-export>`_ that allows users to download data from the table in a variety of formats including XML, JSON, CSV and Excel spreedsheets. 

Bootstrap-Table and Data Interrogator work well together, and just require loading  the correct javascript libraries for Bootstrap-Table, and altering the ``data_interrogator/interrogation_room.html`` template to add the right data attributes for driving the javascript, for example::

    <table class="table" data-toggle="table"
           data-toolbar="#toolbar"
           data-search="true"
           data-show-filter="true"
           data-show-toggle="true"
           data-show-columns="true"
           data-show-export="true"
    >
    {# rest of template goes here #}
