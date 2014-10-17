import argparse
import os
import os.path
import subprocess

from spiny import environment
from ConfigParser import ConfigParser


def install_virtualenv(envname, envdict, venv_dir):
    if not os.path.exists(venv_dir):
        os.mkdir(venv_dir)

    exepath = envdict['path']
    #subprocess.Popen([exepath, '-m', 'virtualenv', os.path.join(venv_dir, envname)])


def main():
    parser = argparse.ArgumentParser(
        description='Frabble the foo and the bars')

    parser.add_argument(
        '--config',
        '-c',
        action='store',
        default='spiny.conf',
        metavar='<filename>',
        type=str,
        help='The config file to use. Defaults "to spiny.conf"')

    parser.add_argument(
        'configvar',
        action='store',
        type=str,
        nargs='*',
        help='Override a config variable by "section:variable=value" '
             'Example: "spiny:venv_dir=.venv"')

    args = parser.parse_args()
    run(args.config, args.configvar)


def run(config_file, overrides):
    # Parse the config files
    if 'HOME' in os.environ:
        home = os.environ['HOME']
    else:
        home = '~'

    # User settings
    settings_file = os.path.join(home, '.config', 'spiny.conf')

    config = ConfigParser()
    config.read([config_file, settings_file])

    for override in overrides:
        if ':' not in override or '=' not in override:
            raise ValueError('%s is not a valid config variable. It should be "section:variable=value"')
        section, rest = override.split(':', 1)
        option, value = rest.split('=', 1)
        config.set(section.strip(), option.strip(), value.strip())

    # Get the verified environments
    pythons = environment.get_pythons(config)

    # Install a virtualenv for each environment
    if config.has_option('spiny', 'venv_dir'):
        venv_dir = config.get('spiny', 'venv_dir')
    else:
        venv_dir = '.venv'
    venv_dir = os.path.abspath(venv_dir)
    for env in config.get('spiny', 'environments').split():
        # Run virtualenvs
        install_virtualenv(env, pythons[env], venv_dir)

    # Run the test commands
    print config.items('spiny')

