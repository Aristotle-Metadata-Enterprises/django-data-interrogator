# Want to help maintain this library?

There is a `/dev/` directory with a docker-compose stack you can use to bring up a database and clean development environment.

## Running tests

Django Data Interrogator is tested using a docker-compose environment so tests can be easily run locally against MariaDB, Postgres and SQLite.

To run tests:
*  ``cd ./dev`` 
* Start the docker environment - ``docker-compose up``
* Start a development shell - ``docker-compose exec dev bash``
* Run tests - ``tox``

## Manually testing the interface

*  ``cd ./dev`` 
* Start the docker environment - ``docker-compose up``
* Start a development shell - ``docker-compose exec dev bash``
* Setup the database - ``django-admin migrate``
* Load some sample data - ``django-admin load_data data.json``
* Start the dev server -  ``django-admin runserver 0.0.0.0:8001``
* Open ``localhost:8001`` in your browser
