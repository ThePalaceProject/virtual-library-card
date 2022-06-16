# Virtual Library Cards

## Prerequisites

Python 3+ must be installed, and a SQL database must be available.

## Notes

- The project settings are split into 3 files inside the "settings" directory. "base.py" contains the common
  definitions, while "dev.py" and "prod.py" contain specific parameters for development and production environments
  (see -
  [Strategy based on multiple settings files](https://simpleisbetterthancomplex.com/tips/2017/07/03/django-tip-20-working-with-multiple-settings-modules.html)
  ).
- IMPORTANT: A `settings/prod_pg.py` file has been added with sample PostgreSQL config. So replace "prod.py" by
  "prod_pg.py" everywhere in what follows if needed...
- The website and API are in the same Django project and app. The `HAS_API` and `HAS_WEBSITE` flags in the
  `settings/prod.py` allow to control what is deployed.

## Deploying with Docker

### 1. Build docker container

This step builds the docker container. Eventually you will be able to pull container for dockerhub.

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

## Deploying for production

### 1. Clone the repository

`cd` to the directory where you want to deploy the project files (as specified in the apache conf file), and clone the repository:

    git clone https://jmgeffroy@bitbucket.org/mantano/virtual_library_card.git

### 2. Create and initialize a Python virtual env

    pip install --upgrade pip
    pip install virtualenv
    python3 -m venv venv
    source venv/bin/activate
    poetry install --no-dev

Note: activate the virtual env before installing the requirements.

### 3. Collect the static files

The static files must be "collected" to the dedicated directory:

    python ./manage.py collectstatic --settings=virtual_library_card.settings.prod

This directory is by default `static`, inside the project root, but you can adjust it to whatever you want, as described
in section "8. Prepare the web server".

See [django documentation](https://docs.djangoproject.com/en/2.2/howto/deployment/wsgi/modwsgi/#serving-files).

### 4. Create a database and adjust the database connection parameters`

The database connection parameters for a development (resp. production) environment are located in the `settings/dev.py`
(resp.`settings/prod.py` and `settings/prod_pg.py`) files:

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

Note: in the previous command, please use `prod_pg` if you are using PostgreSQL.

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

The `sample-apache-config/vlc-website.conf` file contains a sample Apache conf file for the website (exact same to
deploy the API). This file must be placed into /etc/apache2/sites-available, and be enabled with `a2enmod`.

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

## Updating the project

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

### Other Settings

`JWT_SECRET` needs to be set to any string, longer the better.
The code uses this value to sign JWT tokens, which are currently only used for user verification emails.
`BASE_URL` should be the target hosting environments hostname address with http schema,
eg. locally it is "http://localhost:8000", where as in the cloud it would be something like "https://vlc.example.com"

### 6. Select what (website or/and API) will be deployed

The website and API are in the same Django project and app. The `HAS_API` and `HAS_WEBSITE` flags allow to control
what is deployed. You can adjust these values in the `settings/dev.py` file.
Typically, on a developer machine you will set both to `True`.

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

References

- [How To Serve Django Applications](https://www.digitalocean.com/community/tutorials/how-to-serve-django-applications-with-apache-and-mod_wsgi-on-debian-8)
- [Deploy Django on Apache with Virtualenv and mod_wsgi](https://www.thecodeship.com/deployment/deploy-django-apache-virtualenv-and-mod_wsgi/)
