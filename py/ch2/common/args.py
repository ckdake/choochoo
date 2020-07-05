from re import sub
from typing import MutableMapping

from .names import BIND, PORT, OFF, LIGHT, DARK


class NamespaceWithVariables(MutableMapping):

    def __init__(self, ns):
        self._dict = dict(vars(ns))

    def __getitem__(self, name):
        try:
            value = self._dict[name]
        except KeyError:
            value = self._dict[sub('-', '_', name)]
        return value

    def __setitem__(self, name, value):
        self._dict[name] = value

    def __delitem__(self, name):
        del self._dict[name]

    def __iter__(self):
        return iter(self._dict)

    def __len__(self):
        return len(self.__dict__)


def mm(name): return '--' + name


def m(name): return '-' + name


def no(name): return 'no-%s' % name


def add_server_args(cmd, prefix='', default_address='localhost', default_port=80):
    if prefix: prefix += '-'
    cmd.add_argument(mm(prefix + BIND), default='localhost', metavar='ADDRESS',
                     help='bind address' + f' (default {default_address})' if default_address else '')
    cmd.add_argument(mm(prefix + PORT), default=default_port, type=int, metavar='PORT',
                     help=f'port' + f' (default {default_port})' if default_port else '')


def color(color):
    if color.lower() not in (LIGHT, DARK, OFF):
        raise Exception(f'Bad color: {color} ({LIGHT}|{DARK}|{OFF})')
    return color
