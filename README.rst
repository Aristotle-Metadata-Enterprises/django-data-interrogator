django-data-interrogator
========================

``django-data-interrogator`` is a plug in table builder that allows users to easily interrogate information from a django database. In essence it provides a smart and sane frontend for building tabular data from the django database queryset API - specifically ``values``, ``filter``, ``order_by`` and a handful of annotations.

.. contents::

Installing
----------

Add the *Data Interrogator* to your ``INSTALLED_APPS``:\

.. code-block:: python

   INSTALLED_APPS = (
     # ...
     'data_interrogator',
   )

Quickstart
----------

#. Make a list of base_models (models you wish to interrogate) and enter models into *witness protection* (models you want to disallow access to):

.. code-block:: python 

    DATA_INTERROGATION_DOSSIER = {
        'base_models': [
            {'model':("yourapplabel","YourModelName")},
            {'model':("yourapplabel","YourOtherModelName")},
         ],
        'excluded_models' : ["User","Revision","Version"]
    }

Notes: ``base_models`` are used to query the django ``ContentType`` database. The values in ``excluded_models`` are matched against columns that might be returned, and any columns that match will be dropped from output.

1. Make a view to capture form requests and pass the request off to the *interrogator*:

.. code-block:: python 

    def custom_table(request):
        return interrogation_room(request, template='your/interrogation/template.html')

2. Make sure your template can handle the interrogation procedures::

.. code-block:: django

    {% load data_interrogator %}

    {% lineup %} {# loads the form for selecting columns #}
    {% interrogation_room %} {# loads the table where data is displayed #}
    
3. Thats it!

Extra dossier configuration
---------------------------

The *Interrogation dossier* is a powerful way of altering how data is output. Along with specifying a model that can be a base_model, you can specify ``wrapsheets`` for them - i.e. special ways of displaying columns.

Below is an example dossier for a single model, with a wrapsheet for the column ``foo`` on the model ``YourModel``:

.. code-block:: python

    DATA_INTERROGATION_DOSSIER = {
        'base_models': [
          { "model":("yourappname","YourModel"),
            "wrap_sheets": {
                "foo": {
                    "columns": ['pk','bar'],
                    "template": "yourapp/special_columns/for_foo.html",
                }
           },
        ]
     }

The ``columns`` value in the ``custom_cell_display`` specified additional columns of data to be retrieved when querying the specified attribute. So in the above example, whenever anyone requests the ``foo`` attribute when interrogating the ``YourModel`` model the ``pk`` and ``bar`` fields will also be retrieved, *but will not be visible in the output table*. However they will be accessible in the ``yourapp/special_columns/for_foo.html`` template which will be used when rendering the ``<td>`` table cell in the table.

Bootstrap your way to a nicer interrogation room
------------------------------------------------

*Data Interrogator* integrates nicely with `Bootstrap <http://getbootstrap.com>`_ and by default adds a ``table`` class `to use Bootstrap's built in styling for tables <http://getbootstrap.com/css/#tables>`_. If you want to do additional customisation of the "interrogation room" table, just override the ``data_interrogator/table_display.html`` template. For example to convert the interrogation room table into one that is responsive and has table striping, just change the template to that below:

.. code-block:: django

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

Bootstrap-Table and Data Interrogator work well together, and just require loading  the correct javascript libraries for Bootstrap-Table, and altering the ``data_interrogator/table_display.html`` template to add the right data attributes for driving the javascript, for example:

.. code-block:: django

    <table class="table" data-toggle="table"
           data-toolbar="#toolbar"
           data-search="true"
           data-show-filter="true"
           data-show-toggle="true"
           data-show-columns="true"
           data-show-export="true"
    >
    {# rest of template goes here #}

How to interrogate your data
----------------------------

If we assume that we have an app with a model for Police Officers with the following models:

.. code-block:: python

    class PoliceOfficer:
        name = CharField(max_length=150)
        rank = CharField(max_length=150)
        precint = ForeignKey(Precinct)
        
    class Precinct:
        name = CharField(max_length=150)
        number = IntegerField()
        captain = ForeignKey(PoliceOfficer, related_name="command")
    
    class Arrest:
        officer = ForeignKey(PoliceOfficer)
        perp_name = CharField(max_length=150)
        crime = CharField(max_length=150)

With all of the above set up, you should have a page that looks similar to that below.

.. image:: https://cloud.githubusercontent.com/assets/2173174/8870301/4511a998-3230-11e5-94e0-2a60968a814a.png

In the above image we can see a user can add or remove filtering constraints, columns and ordering fields. For example, in the above image, we are querying the "Person" model which contains a list of police officers, filtering where the ``rank`` field equals "Detective" and extracting the persons name, precinct number, precinct captain's name, and the count of their arrests, all of which is ordered by arrests largest-to-smallest.

================= =============== ===================== =============
    name          precinct.number precinct.captain.name count(arrest)
================= =============== ===================== =============
Jake Peralta                  99      Raymond Holt            177
Amy Santiago                  99      Raymond Holt            168
Roza Diaz                     99      Raymond Holt             77
Charles Boyle                 99      Raymond Holt             67
Michael Hitchcock             99      Raymond Holt              8
Norm Scully                   99      Raymond Holt              6
================= =============== ===================== =============

Behind the scenes the data interrogator converts text fields into a format that can be used within the django QuerySet API. In this example, dots (``.``) become double underscores (``__``) that allow a query to follow foreign keys. So in the above query the column ``precinct.number`` becomes ``precinct__number``, this can then be fed into the `values function in the django queryset API <https://docs.djangoproject.com/en/1.8/ref/models/querysets/#django.db.models.query.QuerySet.values>`. While 'dot notation' is used for simplicity regular django column names with underscores can be used.

Generating counts, minimums and maximums
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
A small number of `aggregate functions <https://docs.djangoproject.com/en/1.8/ref/models/querysets/#aggregate>`_ are available from the front end - currently ``Count()``, ``Max()`` and ``Min()``. Since these need to be set up in code, these need to be exectued using special syntax - that is just wrapping a column name in the aggregating command (like demonstrated above), with the argument ``count(arrests)``.

Cross-table comparisons in filters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Most django queries in filters match a field with a given string, however there are cases where you would like to compare values between columns. These can be achieved by using ``F()`` statements in django. A user can specify that a filter should compare columns with an ``F()`` statement by using a ``double equals`` in the filter. If for example, we wanted to see a list of officers *who had also been arrested* we could do this by filtering with ``name==arrest.perp_name`` which would be normalised in django to ``QuerySet.filter(name=F('perp_name'))``.


Setting up a test environment
=============================

* pipenv install
* pipenv shell
* PYTHONPATH=.:./app:./app/shop DJANGO_SETTINGS_MODULE=app.settings django-admin [YOUR_COMMAND]

To play with data load the shops fixture
* PYTHONPATH=.:./app:./app/shop DJANGO_SETTINGS_MODULE=app.settings django-admin migrate
* PYTHONPATH=.:./app:./app/shop DJANGO_SETTINGS_MODULE=app.settings django-admin loaddata data.json
