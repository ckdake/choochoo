
from logging import getLogger
from os import unlink

from sqlalchemy_utils import create_database, drop_database, database_exists
from uritools import urisplit

from .args import SUB_COMMAND, LIST, PROFILE, SHOW, DB_VERSION, FORCE, DELETE
from ..common.names import POSTGRESQL, SQLITE, URI
from ..common.args import mm
from .help import Markdown
from ..config.utils import profiles, get_profile
from ..common.io import clean_path
from ..common.sql import database_really_exists

log = getLogger(__name__)


def database(config):
    '''
## database

    > ch2 database load --uri URI [--delete] PROFILE

Load the initial database schema.

    > ch2 database list

List the available profiles.

    > ch2 database show

Show the current database state.

    > ch2 database delete

Delete the current database.
    '''
    args = config.args
    action = args[SUB_COMMAND]
    if action == SHOW:
        show(config)
    elif action == LIST:
        list()
    elif action == DELETE:
        uri = args[URI] or config.get_uri()
        if not uri: raise Exception('No current database is defined')
        delete(config)
    else:
        load(config, args[PROFILE], args[FORCE])


def show(data):
    uri = data.get_uri()
    if uri:
        print(f'{URI}:     {uri}')
        print(f'version: {DB_VERSION}')
        print(f'exists:  {database_really_exists(uri)}')
    else:
        print('no database configured')
    return


def list():
    fmt = Markdown()
    for name in profiles():
        fn, spec = get_profile(name)
        if fn.__doc__:
            fmt.print(fn.__doc__)
        else:
            print(f' ## {name} - lacks docstring\n')


def delete(data):
    uri = data.get_uri()
    if database_exists(uri):
        log.debug(f'Deleting database at {uri}')
        uri_parts = urisplit(uri)
        if uri_parts.scheme == SQLITE:
            path = clean_path(uri_parts.path)
            log.warning(f'Deleting {path}')
            unlink(path)
        elif uri_parts.scheme == POSTGRESQL:
            drop_database(uri)
        else:
            raise Exception(f'Unsupported URI {uri}')
    else:
        log.warning(f'No database at {uri} (so not deleting)')


def delete_and_check(data, force=False):
    if force: delete(data)
    uri = data.get_uri()
    data.reset()
    if database_exists(uri) and not data.db.no_data():
        raise Exception(f'A schema exists at {uri} (use {mm(FORCE)}?)')


def write(uri, profile, data):
    fn, spec = get_profile(profile)
    log.info(f'Loading profile {profile}')
    db = data.get_database(uri)  # writes schema automatically
    with db.session_context() as s:
        fn(s, data)
    log.info(f'Profile {profile} loaded successfully')


def create(uri):
    log.debug(f'Creating database at {uri}')
    create_database(uri)


def load(data, profile, force=False):
    uri = data.get_uri()
    delete_and_check(data, force=force)
    create(uri)
    write(uri, profile, data)
