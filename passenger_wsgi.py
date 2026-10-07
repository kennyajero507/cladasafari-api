"""
Entry point for cPanel / DirectAdmin "Setup Python App" (Phusion Passenger on
CloudLinux). Point the app's startup file at this module and its entry point
at `application`.

Passenger strips the app's mount point from the request path: with the app
mounted at /api, a request for /api/tours arrives as SCRIPT_NAME=/api and
PATH_INFO=/tours. The URLconf is written against the full path (api/...,
api/uploads/...), so the mount point is put back before Django sees it. On a
host of its own (api.cladasafaribliss.com) SCRIPT_NAME is empty and nothing
changes.
"""
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

from config.wsgi import application as django_application  # noqa: E402


def application(environ, start_response):
    mount = environ.get('SCRIPT_NAME', '')
    if mount:
        environ['PATH_INFO'] = mount + environ.get('PATH_INFO', '')
        environ['SCRIPT_NAME'] = ''
    return django_application(environ, start_response)
