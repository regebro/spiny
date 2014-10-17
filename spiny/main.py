import argparse
import os
import os.path
import subprocess
import sys

from spiny import environment
from ConfigParser import ConfigParser


def install_virtualenvs(envnames, pythons, venv_dir):
    if not os.path.exists(venv_dir):
        os.mkdir(venv_dir)

    processes = []
    for envname in envnames:
        envdict = pythons[envname]
        exepath = envdict['path']
        envpath = os.path.join(venv_dir, envname)

        if envdict['virtualenv'] == 'internal':
            command = [exepath, '-m', 'virtualenv', envpath]
        else:
            command = [sys.executable, '-m', 'virtualenv',
                       '-p', exepath, envpath]

        processes.append(subprocess.Popen(command,
                                          stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE))

    for process in processes:
        process.wait()
        # TODO: Log errors
        print(process.stdout.read())

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
    envs = config.get('spiny', 'environments').split()
    # Run virtualenvs
    install_virtualenvs(envs, pythons, venv_dir)

    # Run commands

