# Virtual Library Card

[![Test](https://github.com/ThePalaceProject/virtual-library-card/actions/workflows/test.yml/badge.svg)](https://github.com/ThePalaceProject/virtual-library-card/actions/workflows/test.yml)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
![Python: 3.7,3.8,3.9,3.10](https://img.shields.io/badge/Python-3.7%20%7C%203.8%20%7C%203.9%20%7C%203.10-blue)

## Prerequisites

Python 3.7+ must be installed, and a SQL database must be available.

## Notes

- The project settings are split into 3 files inside the "settings" directory. "base.py" contains the common
  definitions, while "dev.py" and "prod.py" contain specific parameters for development and production environments
  (see -
  [Strategy based on multiple settings files](https://simpleisbetterthancomplex.com/tips/2017/07/03/django-tip-20-working-with-multiple-settings-modules.html)
  ).
- The website and API are in the same Django project and app. The `HAS_API` and `HAS_WEBSITE` flags in the
  `settings/prod.py` allow to control what is deployed.

## Deploying for production

### 1. Clone the repository

`cd` to the directory where you want to deploy the project files (as specified in the apache conf file), and clone the repository:

    git clone git@github.com:ThePalaceProject/virtual-library-card.git

### 2. Create and initialize a Python virtual env

    pip install --upgrade pip
    pip install virtualenv
    python3 -m venv venv
    source venv/bin/activate
    poetry install --only-root

Note: activate the virtual env before installing the requirements.

### 3. Collect the static files

The static files must be "collected" to the dedicated directory:

    python ./manage.py collectstatic --settings=virtual_library_card.settings.prod

This directory is by default `static`, inside the project root, but you can adjust it to whatever you want, as described
in section "8. Prepare the web server".

See [django documentation](https://docs.djangoproject.com/en/2.2/howto/deployment/wsgi/modwsgi/#serving-files).

### 4. Create a database and adjust the database connection parameters`

The database connection parameters for a development (resp. production) environment are located in the `settings/dev.py`
(resp.`settings/prod.py`) files:

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'virtual_library_card',
            'USER': '<db_user>',
            'PASSWORD': '<db_password>',
            'HOST': '<db_host>',
            'PORT': '<db_port>',
        }
    }

### 5. Create / update the database schema

After the initial clone and subsequent `git pull` commands, the database schema must be updated by the following command:

    python3 manage.py migrate --settings=virtual_library_card.settings.prod

### 6. Create the superuser

    python manage.py createsuperuser --settings=virtual_library_card.settings.prod

Notes:

- This will also create the "default" library, which can be customized through a few settings in `settings/base.py`:

        DEFAULT_SUPERUSER_LIBRARY_NAME = "Lyrasis"
        DEFAULT_SUPERUSER_LIBRARY_IDENTIFIER = "lyra"
        DEFAULT_SUPERUSER_LIBRARY_PREFIX = "0123"
        DEFAULT_SUPERUSER_LIBRARY_STATE = "NY"

- The pseudo of the superuser can be also configured in the settings files:

        DEFAULT_SUPERUSER_FIRST_NAME = "superuser"

### 7. Select what (website or/and API) will be deployed

The website and API are in the same Django project and app. The `HAS_API` and `HAS_WEBSITE` flags allow to control
what is deployed.
You can adjust these values in the `settings/prod.py` file.

### 8. Prepare the web server

We are using Apache 2 in the sample deployment. See
[modwsgi docs](https://modwsgi.readthedocs.io/en/develop/user-guides/virtual-environments.html#embedded-mode-single-application)
for details. `mod_wsgi` must be installed and enabled.

Ensure your apache2 was installed with the same python version as your virtualenv

The `sample-apache-config/vlc-website.conf` file contains a sample Apache conf file for the website (exact same to
deploy the API). This file must be placed into /etc/apache2/sites-available, and be enabled with `a2ensite`.

In this file, adjust:
- The project code root directory
- The static and media files directories

By default, the static files are placed in the `static` subdirectory. If you want to place them anywhere outside, you
must adjust the following:
- in the `settings/base.py`, you must adjust the `STATICFILES_DIR` param
- the Apache config file section related to the static and media files:

        Alias /media/ <path_to_deployment_dir>/media/
        Alias /static/ <path_to_deployment_dir>/static/

         <Directory <path_to_deployment_dir>/media>
          Require all granted
         </Directory>

         <Directory <path_to_deployment_dir>/static>
          Require all granted
         </Directory>

### 9. Start the web server (Apache)

Typically:

    sudo apache2ctl restart

### Updating the project

    git pull
    python ./manage.py collectstatic --settings=virtual_library_card.settings.prod
    python manage.py migrate --settings=virtual_library_card.settings.prod

Some changes in the code may require restarting the web server, too:

    sudo apache2ctl restart

## Setting up the project on a DEVELOPER machine

The steps are mostly the same, except that on a developer machine, Apache won't usually be used. Instead, we use django's
`runserver` command`

### 1. Clone the repository

`cd` to the directory where you want to deploy the project files (as specified in the apache conf file), and clone the repository:

    git clone git@github.com:ThePalaceProject/virtual-library-card.git
    python ./manage.py collectstatic --settings=virtual_library_card.settings.prod

### 2. Create and initialize a Python virtual env

    pip install --upgrade pip
    pip install virtualenv
    python3 -m venv venv
    source venv/bin/activate
    poetry install

Note: activate the virtual env before installing the requirements

### 3. Adjust the database connection parameters

The database connection parameters for a development (resp. production) environment are located in the `settings/dev.py`
(resp.`settings/prod.py`) files:

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': 'virtual_library_card',
            'USER': 'vlcdbuser',
            'PASSWORD': 'vlc2020',
            'HOST': 'localhost',
            'PORT': '',
        }
    }

### 4. Create / update the database schema

After the initial clone and subsequent `git pull` commands, the database schema must be updated by the following command:

    python manage.py migrate --settings=virtual_library_card.settings.prod

### 5. Create the superuser

    python manage.py createsuperuser --settings=virtual_library_card.settings.prod

Notes:

- This will also create the "default" library, which can be customized through a few settings in `settings/base.py`:

        DEFAULT_SUPERUSER_LIBRARY_NAME = "Lyrasis"
        DEFAULT_SUPERUSER_LIBRARY_IDENTIFIER = "lyra"
        DEFAULT_SUPERUSER_LIBRARY_PREFIX = "0123"
        DEFAULT_SUPERUSER_LIBRARY_STATE = "NY"

- The pseudo of the superuser can be also configured in the settings files:

        DEFAULT_SUPERUSER_FIRST_NAME = "superuser"

### 6. Select what (website or/and API) will be deployed

The website and API are in the same Django project and app. The `HAS_API` and `HAS_WEBSITE` flags allow to control
what is deployed. You can adjust these values in the `settings/dev.py` file.
Typically, on a developer machine you will set both to `True`.

## Other settings

The `RECAPTCHA_PUBLIC_KEY` and `RECAPTCHA_PRIVATE_KEY` must be set if the `captcha` django plugin
is installed via the `INSTALLED_APPS` setting.
If the `catcha` App is not in the `INSTALLED_APPS` setting, the signup flow will silently remove the need for
captcha to be present on that page.

### 7. Start the web server (runserver)

### 8. Schedule clear_sessions in crontab

    0 3 * * * cd <project_root> && <project_root>/venv/bin/python <project_root>/manage.py clearsessions  --settings=virtual_library_card.settings.prod

#### Through the command-line

Make sure the virtual is activated before launching the following command:

    python3 manage.py runserver cms.mantano.com:8000 --settings=virtual_library_card.settings.dev

#### Through the PyCharm IDE

You must first configure the project to use the virtual environment, as described in the
[PyCharm documentation](https://www.jetbrains.com/help/pycharm/creating-virtual-environment.html).

Then, the server can be started thanks to the "Run dropdown":
![Run dropdown screenshot](doc/screenshots/PyCharmRunDropdown.png)

### 8. What to do before pushing code modifications

1. Make sure poetry lock file us up to date

    poetry lock

2. Update and compile the translations

    python3 manage.py makemessages --settings=virtual_library_card.settings.dev
    python3 manage.py compilemessages --settings=virtual_library_card.settings.dev

3. Run pre-commit

## Testing & CI

This project runs all the unit tests through Github Actions for new pull requests and when merging into the default
`main` branch. The relevant file can be found in `.github/workflows/test.yml`. When contributing updates or fixes,
it's required for the test Github Action to pass for all python environments.

### Code Style

Code style on this project is linted using [pre-commit](https://pre-commit.com/). This python application is included
in our `pyproject.toml` file, so if you have the applications requirements installed it should be available. pre-commit
is run automatically on each push and PR.

You can run it manually on all files with the command: `pre-commit run --all-files`.

For more details about our code style, see the
[code style section of the circulation README](https://github.com/ThePalaceProject/circulation#code-style).

### Testing

Github Actions runs our unit tests against different Python versions automatically using
[tox](https://tox.readthedocs.io/en/latest/). `tox` is included in our development dependencies, so it should be
available once you run `poetry install`.

Tox has an environment for each python version and an optional `-docker` factor that will automatically use docker to
deploy service container used for the tests. You can select the environment you would like to test with the tox `-e`
flag.

#### Environments

| Environment | Python Version |
| ----------- | -------------- |
| py37        | Python 3.7     |
| py38        | Python 3.8     |
| py39        | Python 3.9     |
| py310       | Python 3.10    |

All of these environments are tested by default when running tox. To test one specific environment you can use the `-e`
flag.

Test Python 3.8

    tox -e py38

You need to have the Python versions you are testing against installed on your local system. `tox` searches the system
for installed Python versions, but does not install new Python versions. If `tox` doesn't find the Python version its
looking for it will give an `InterpreterNotFound` error.

[Pyenv](https://github.com/pyenv/pyenv) is a useful tool to install multiple Python versions, if you need to install
missing Python versions in your system for local testing.

#### Docker

If you install `tox-docker` tox will take care of setting up all the service containers necessary to run the unit tests
and pass the correct environment variables to configure the tests to use these services. Using `tox-docker` is not
required, but it is the recommended way to run the tests locally, since it runs the tests in the same way they are run
on Github Actions. `tox-docker` is included in the project's development dependencies, so it should always be available.

The docker functionality is included in a `docker` factor that can be added to the environment. To run an environment
with a particular factor you add it to the end of the environment.

Test with Python 3.8 using docker containers for the services.

    tox -e py38-docker

#### Pytest

Tests are performed using [pytest-django](https://pytest-django.readthedocs.io/en/latest/index.html). The tests
require a database, and use the settings configured in [dev.py](virtual_library_card/settings/dev.py). The test database
uses the database name configured in `dev.py` with `test_` prepended to it (`test_virtual_library_card_dev`). This
database will be created automatically by the tests, and cleaned up afterwords. So the database user must have
permission to create and drop databases.

### References

- [How To Serve Django Applications](https://www.digitalocean.com/community/tutorials/how-to-serve-django-applications-with-apache-and-mod_wsgi-on-debian-8)
- [Deploy Django on Apache with Virtualenv and mod_wsgi](https://www.thecodeship.com/deployment/deploy-django-apache-virtualenv-and-mod_wsgi/)

## Deploying with Docker

### 1. Build docker container

After cloning the repository, this step builds the docker container.
Eventually you will be able to pull the container from dockerhub.

    docker build -t virtual_libary_card .

### 2. Create PostgreSQL Container (Only for testing)

Either create a new database in the production PostgreSQL Database. Or use the docker PostgreSQL container for testing.

    docker run -d --name pg --rm -e POSTGRES_USER=vlc -e POSTGRES_PASSWORD=test -e POSTGRES_DB=virtual_library_card postgres:12

### 3. Create settings file

Create the settings file for the app and bind mount it into the container. The `virtual_library_card/settings/dev.py`
is an example of this file, and in most cases can be used for basic testing.

### 4. Start container

    docker run --name vlc --rm -p 8000:8000 -e SUPERUSER_EMAIL=test@test.com -e SUPERUSER_PASSWORD=test -e \
      DJANGO_SETTINGS_MODULE=virtual_library_card.settings.dev --link pg virtual_library_card

### 5. View site

The site should be available in your browser for testing at `https://localhost:8000`.
