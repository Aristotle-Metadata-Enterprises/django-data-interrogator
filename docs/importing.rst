Importing additional data
=========================

*The Data Interrogator helps you a dragnet for bulk processing base_models.*

Rough translation: The Data Interrogator is only as good as the data you provide,
and in a lot of cases data is trapped in CSVs or Excel spreadsheets.
To help migrate as much of your data as quickly as possible into a structured database
the Interrogator provides a csv importer.

You can run it like so::

    ./manage.py dragnet ./path/filename.csv [options]
    
The available options are:

  ``-m, --model`` - The model this csv will populate. Must be of the form ``app_label.model`` (optional, see below)
  ``-s, --sep`` - CSV column separator (default: `,`), `tab` can be used to denote a tab-separated file.
  ``-D, --debug`` - Enable debug mode. This will load only the first line, and allow all exceptions to propagate up.
  ``-v`` - Verbosity level. Can be 0,1,2,3. Higher levels print more messages.
  
If the model option is left blank, the filename will be used to determine the model.
To enable this make sure the filename is of the form::

    app_label.model_name.csv
  
How to name headings
--------------------

1. Headings must be named to match the appropriate field. If you have a field ``first_name``, label that column ``first_name``
2. To ignore a column, preceed it with an underscore - ``_``. This is useful where you have a column that is an ID to another table, but want to include a label that makes it easier.
3. To assign foreign key relationships use dot notation.