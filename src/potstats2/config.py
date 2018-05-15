import ast
import configparser
import os
import os.path
import sys
from collections import namedtuple

NO_DEFAULT = object()
Setting = namedtuple('Setting', 'description default')

SETTINGS = {
    'DB': Setting('Database url, see https://docs.sqlalchemy.org/en/latest/core/engines.html#database-urls',
                  'postgresql://localhost/potstats2'),
    'REQUEST_DELAY': Setting('Delay between requests, not including request processing time.', '0.05'),
    'DEBUG': Setting('Enable post-mortem debugging', 'True'),
}

INI_PATH = os.path.expanduser('~/.config/potstats2.ini')


class ConfigurationError(RuntimeError):
    pass


def get(setting, ini_path=INI_PATH):
    assert setting in SETTINGS
    env_var_name = 'POTSTATS2_' + setting
    s = SETTINGS[setting]
    try:
        return os.environ[env_var_name]
    except KeyError:
        config = configparser.ConfigParser()
        try:
            with open(ini_path, 'r') as fd:
                config.read_file(fd)
        except FileNotFoundError as fnfe:
            if s.default is not NO_DEFAULT:
                return s.default
            raise ConfigurationError('Setting "{setting}" not configured '
                                     '(no {env_var_name} env var set, '
                                     'no {ini_path} config file, '
                                     'no default)'.format_map(locals()))
        if 'potstats2' not in config.sections():
            raise ConfigurationError('Missing [potstats2] section from config file ({ini_path})'.format_map(locals()))
        ps = config['potstats2']
        if setting not in ps:
            if s.default is not NO_DEFAULT:
                return s.default
            raise ConfigurationError('Setting "{setting}" not configured '
                                     '(no {env_var_name} env var set, '
                                     'not in {ini_path} config file, '
                                     'no default)'.format_map(locals()))
        return ps[setting]


def enter_postmortem_debugger(type, value, tb):
    # https://stackoverflow.com/a/242531/675646
    if hasattr(sys, 'ps1') or not sys.stderr.isatty():
    # we are in interactive mode or we don't have a tty-like
    # device, so we call the default hook
        sys.__excepthook__(type, value, tb)
    else:
        import traceback, pdb
        # we are NOT in interactive mode, print the exception...
        traceback.print_exception(type, value, tb)
        print()
        # ...then start the debugger in post-mortem mode.
        # pdb.pm() # deprecated
        pdb.post_mortem(tb) # more "modern"


def setup_debugger():
    if ast.literal_eval(get('DEBUG')):
        sys.excepthook = enter_postmortem_debugger
