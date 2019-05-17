[![CircleCI](https://circleci.com/gh/elpaso/g3w-admin/tree/dev.svg?style=svg)](https://circleci.com/gh/elpaso/g3w-admin/tree/dev)

# G3W-SUITE

G3W-ADMIN admin server module for G3W-SUITE.

G3W-SUITE works with **QGIS-Server LTR versions**, so at the moment works with **QGIS-Server 2.18.x LTR**

The following instructions are for a Ubuntu 16.04 LTS.

## Installation of node.js and Yarn
G3W-ADMIN use javacript package manager [**Yarn**](https://yarnpkg.com/) and [**Node.js**](https://nodejs.org/it/)

```bash
sudo apt-get install -y nodejs-legacy npm
```

for install Yarn follow main installation instructions:

https://yarnpkg.com/en/docs/install#debian-stable

## Create virtualenv

[**Virtualenv**](https://virtualenv.pypa.io/en/stable/)

The following instructions are for python 2

Install python pip

```bash
sudo apt-get install python-pip
```

now we can install virtualenvwrapper
```bash
sudo pip install virtualenvwrapper
```

To activate virtuenvwrapper on system login, add follow lines to 'bashrc' config file of your user
```bash
nano ~/.bashrc
....
export WORKON_HOME=<path_to_virtualenvs_directory>
source /usr/local/bin/virtualenvwrapper.sh
```

## Virtualenv creation
To create a virtualnenv is sufficent call mkvirtualenv commando follow by the identification name for virtualenv
```bash
mkvirtualenv g3wsuite
```

## Install G3W-SUITE

First step is install dev libraries packages for python module to install with requiriments.txt

```bash
sudo apt-get install -y \
    libxml2-dev \
    libxslt-dev \
    postgresql-server-dev-all \
    libgdal-dev \
    python-dev
```

after is necessary install the correct python module for GDAL library, check your version and install correct module

```bash
export CPLUS_INCLUDE_PATH=/usr/include/gdal
export C_INCLUDE_PATH=/usr/include/gdal

pip install GDAL==<installed_version or closest>
```

### Set local_config.py file
G3W-ADMIN is a Django application, and to work is necessary set a config.py file. To start copy local_settings.example.py and set the databse and other:
```bash
cd g3w-admin/g3w-admin/base/settings
cp local_settings_example.py local_settings.py
```

set database, media root and session cookies name:

```python
...

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': '<db_name>',
        'USER': '<db_user>',
        'PASSWORD': '<db_user_password>',
        'HOST': '<db_host>',
        'PORT': '<db_port>',
    }
}

...

DATASOURCE_PATH = '<static_path_to_gis_data_source>'

...

MEDIA_ROOT = '<path_to_media_root>'

...

SESSION_COOKIE_NAME = '<unique_session_id>'
```

### With paver commands

G3W-ADMIN has a series of [paver](http://pythonhosted.org/Paver/) CLI commands to administrate the suite.
After prepared environment if sufficient invoce paver *install* task

```bash
paver install
```

### Run G3W-SUITE

To run the application with paver

```bash
paver start
```

and for stop
```bash
paver stop
```


G3W-ADMIN is a django application so is possibile run app by standard django manage.py commands

```bash
./manage.py runserver
```

## Deploy G3W-SUITE

As other Django application, G3W-SUITE can be deployed by its wsgi capabilities.
On the web if simple to find tutorial for deploy a Django application.

The simpler way is to use [Apache2](https://httpd.apache.org/) as server WEB and its [mod_wsgi](https://en.wikipedia.org/wiki/Mod_wsgi) module.

Alternative solutions are:


* [Apache2](https://httpd.apache.org/) + [mod_proxy](https://httpd.apache.org/docs/2.4/mod/mod_proxy.html) + [Uwsgi](https://uwsgi-docs.readthedocs.io/en/latest/)
* [Apache2](https://httpd.apache.org/) + [mod_proxy](https://httpd.apache.org/docs/2.4/mod/mod_proxy.html) + [Gunicorn](http://gunicorn.org/)
* [Nginx](https://nginx.org/) + [Uwsgi](https://uwsgi-docs.readthedocs.io/en/latest/)
* [Nginx](https://nginx.org/) + [Gunicorn](http://gunicorn.org/)



