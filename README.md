# Virtual Library Card

[![Test](https://github.com/ThePalaceProject/virtual-library-card/actions/workflows/test.yml/badge.svg)](https://github.com/ThePalaceProject/virtual-library-card/actions/workflows/test.yml)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
![Python: 3.10,3.11](https://img.shields.io/badge/Python-3.10%20|%203.11-blue)

## Prerequisites

Python 3.10+ must be installed, and a SQL database must be available.

## Notes

- The project settings are split into 2 files inside the "settings" directory. "base.py" contains the common
  definitions, while "dev.py" contains an example configuration for development.
- The website and API are in the same Django project and app. The `HAS_API` and `HAS_WEBSITE` flags allow
  control over what is deployed.

## Running the application locally

### 1. Clone the repository

    git clone git@github.com:ThePalaceProject/virtual-library-card.git

### 2. Create and initialize a Python virtual env

    pip install --upgrade pip
    pip install virtualenv
    python3 -m venv venv
    source venv/bin/activate
    poetry install --only-root

Note: activate the virtual env before installing the requirements.

### 3. Set up public MinIO bucket (or public AWS S3 bucket)

VLC puts static files into public AWS S3 bucket so to run the VLC locally the easiest will be to run the MinIO locally in
a Docker container. You can read more about MinIO [here](https://min.io/docs/minio/container/index.html).

To run the MinIO in Docker container run:

    docker run -d -p 9000:9000 -p 9001:9001 --name minio \
      -e "MINIO_ROOT_USER=vlc-minio" -e "MINIO_ROOT_PASSWORD=123456789" \
      quay.io/minio/minio server /data --console-address ":9001"

After you have MinIO container running, you will need to create the public bucket to put the static files in.
Log into `http://localhost:9001` with username `vlc-minio` and password `123456789`.
Create bucket named `vlc-test` and make it public. The name for the bucket can be changed inside the settings file by
means of the variable `AWS_STORAGE_BUCKET_NAME`.

### 4. Collect the static files

The static files must be "collected":

    python ./manage.py collectstatic --settings=virtual_library_card.settings.dev

Our default configuration puts these files into a public s3 bucket.

See [django documentation](https://docs.djangoproject.com/en/2.2/howto/deployment/wsgi/modwsgi/#serving-files).

### 5. Create a database and adjust the database connection parameters`

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

### 6. Create / update the database schema

The database schema must be initialized and updated with:

    python3 manage.py migrate --settings=virtual_library_card.settings.dev

### 7. Create the superuser

    python manage.py createsuperuser --settings=virtual_library_card.settings.dev

Notes:

- This will also create the "default" library, which can be customized through a few settings in `settings/dev.py`:

        DEFAULT_SUPERUSER_LIBRARY_NAME
        DEFAULT_SUPERUSER_LIBRARY_IDENTIFIER
        DEFAULT_SUPERUSER_LIBRARY_PREFIX
        DEFAULT_SUPERUSER_LIBRARY_STATE

- The name of the superuser can be also configured in the settings files:

        DEFAULT_SUPERUSER_FIRST_NAME

### 8. Select what (website or/and API) will be deployed

The website and API are in the same Django project and app. The `HAS_API` and `HAS_WEBSITE` flags allow to control
what is deployed.
You can adjust these values in the `settings/dev.py` file.

### 9. Run webserver

#### Development

For development, you can use the Django `runserver` command.

    python manage.py runserver --settings=virtual_library_card.settings.dev

#### UWSGI

For development or production use you can run the application under uwsgi.

    uwsgi --wsgi-file virtual_library_card/wsgi.py --http :8000

## Running the application with docker-compose

We have an example [docker-compose.yml](docker-compose.yml) that can be used as a starting
point for deploying the code to production, or as an easy way to run the application for
development. It runs three containers: postgresql, minio and vlc. It takes care of setting
up the environment variables to configure the containers to talk to one another.

    docker-compose up -d

Then you should be able to access the site at `http://localhost:8000` with the username (test@test.com)
and password (test) defined in [`docker-compose.yml`](./docker-compose.yml).

## Running the application in docker

### 1. Build docker container

After cloning the repository, this step builds the docker container.
Eventually you will be able to pull the container from dockerhub.

    docker build -t virtual_libary_card .

### 2. Create PostgreSQL Container (Only for testing)

Either create a new database in the production PostgreSQL Database. Or use the docker PostgreSQL container for testing.

    docker run -d --name pg --rm -e POSTGRES_USER=vlc -e POSTGRES_PASSWORD=test -e POSTGRES_DB=virtual_library_card postgres:16

### 3. Create settings file

Create the settings file for the app and bind mount it into the container. The `virtual_library_card/settings/dev.py`
is an example of this file, and in most cases can be used for basic testing.

### 4. Start container

    docker run --name vlc --rm -p 8000:8000 -e SUPERUSER_EMAIL=test@test.com -e SUPERUSER_PASSWORD=test -e \
      DJANGO_SETTINGS_MODULE=virtual_library_card.settings.dev --link pg virtual_library_card

### 5. View site

The site should be available in your browser for testing at `https://localhost:8000`.

## Other settings

The `RECAPTCHA_PUBLIC_KEY` and `RECAPTCHA_PRIVATE_KEY` must be set if the `django_recaptcha` django plugin
is installed via the `INSTALLED_APPS` setting.
If the `django_recaptcha` App is not in the `INSTALLED_APPS` setting, the signup flow will silently remove the need for
captcha to be present on that page.

### Environment Variables

**DJANGO_LOG_LEVEL**: Can be a python log level string. It defaults to `INFO`.
All application logging occurs at this defined level.

### AWS S3 Setup

An S3 bucket should be created out-of-band to store uploaded files and static files.
The following variables must be populated in the settings file.

    `DEFAULT_FILE_STORAGE` = "virtual_library_card.storage.S3PublicStorage"
    `STATICFILES_STORAGE` = "virtual_library_card.storage.S3StaticStorage"
    `AWS_STORAGE_BUCKET_NAME` = "The name of the already created S3 bucket"

Optionally, the following settings can be set

    # Either
    `AWS_S3_SESSION_PROFILE` = "profile-name"
    # Or
    `AWS_S3_ACCESS_KEY_ID` = "The AWS access key"
    `AWS_S3_SECRET_ACCESS_KEY` = "The AWS secret key"

In case neither session profile or key-secret are provided, the boto3 "default" session will be used.

Additional optional settings can be added as per the documentation for
[django-storages](https://django-storages.readthedocs.io/en/latest/).
In a development setting the minio container may also be used to mimic
a local S3 deployment, in which case `AWS_S3_ENDPOINT_URL` should also be configured.
Refer [Bitnami Minio](https://hub.docker.com/r/bitnami/minio/).

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
|-------------|----------------|
| py310       | Python 3.10    |
| py311       | Python 3.11    |

All of these environments are tested by default when running tox. To test one specific environment you can use the `-e`
flag.

Test Python 3.10

    tox -e py310

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

Test with Python 3.10 using docker containers for the services.

    tox -e py310-docker

#### Pytest

Tests are performed using [pytest-django](https://pytest-django.readthedocs.io/en/latest/index.html). The tests
require a database, and use the settings configured in [dev.py](virtual_library_card/settings/dev.py). The test database
uses the database name configured in `dev.py` with `test_` prepended to it (`test_virtual_library_card_dev`). This
database will be created automatically by the tests, and cleaned up afterwords. So the database user must have
permission to create and drop databases.
