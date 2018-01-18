# DeviceManager

[![License badge](https://img.shields.io/badge/license-GPL-blue.svg)](https://opensource.org/licenses/GPL-3.0)
[![Docker badge](https://img.shields.io/docker/pulls/dojot/iotagent-json.svg)](https://hub.docker.com/r/dojot/device-manager/)

The DeviceManager handles all operations related to creation, retrieval, update and deletion of devices in dojot. For more information
on that, check [this file](./concepts.md).

## Dependencies

DeviceManager has the following dependencies:

- flask (including flask_sqlalchemy)
- psycopg2
- marshmallow
- requests
- gunicorn
- gevent
- json-logging-py
- kakfa-python

But you won't need to worry about installing any of these - they are automatically installed when starting DeviceManager.
There must be, though, a postgres instance accessible by DeviceManager.

## How to run

If you really need to run DeviceManager as a standalone process (without dojot's wonderful docker-compose), you can execute these commands:

```shell
python setup.py develop
gunicorn device-manager.app:app
```

Keep in mind that running a standalone instance of DeviceManager misses a lot of security checks (such as user identity checks, proper multi-tenancy validations, and so on). In particular, every request sent to DeviceManager needs an access token, which should be retrived from [auth](https://github.com/dojot/auth) component.

## How to use it

There are a few concepts that must be understood to properly use DeviceManager. Visit [this page](concepts.md) to check them out.

This component listens to HTTP requests at port 5000 - all its endpoints are documented [here](apis.html). __IMPORTANT: If you are using all dojot's components (for instance, using a deploy based on [docker-compose](https://github.com/dojot/docker-compose)), it is recommended to visit [dojot's documentation](http://dojotdocs.readthedocs.io/en/latest/apis.html) to check the endpoints for all services (including DeviceManager's)__
