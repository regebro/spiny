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
            # Internal means use the virtualenv for the relevant Python
            command = [exepath, '-m', 'virtualenv', envpath]
        else:
            # External means use the virtualenv for the current Python
            command = [sys.executable, '-m', 'virtualenv',
                       '-p', exepath, envpath]

        processes.append(subprocess.Popen(command,
                                          stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE))

    for process in processes:
        process.wait()
        # TODO: Log errors
        print(process.stdout.read())


def run_commands(envnames, venv_dir, commands):
    """Run a list of commands in each virtualenv"""

    results = {}
    for envname in envnames:
        envpath = os.path.join(venv_dir, envname)
        python = os.path.join(envpath, 'bin', envname)
        environment = {'environment': envpath,
                       'python': python}

        fail = False
        for command in commands:
            command = command.strip().format(**environment)
            result = subprocess.call(command, shell=True)
            if result != 0:
                fail = True
                break

        results[envname] = fail
    return results


def main():
    parser = argparse.ArgumentParser(
        description='Run tests under several Python versions')

    parser.add_argument(
        '--config',
        '-c',
        action='store',
        default='spiny.cfg',
        metavar='<filename>',
        type=str,
        help='The config file to use. Defaults "to spiny.cfg"')

    parser.add_argument(
        'configvar',
        action='store',
        type=str,
        nargs='*',
        metavar='<configvar>',
        help='Override a config variable by "section:variable=value" '
             'Example: "spiny:venv_dir=.venv"')

    args = parser.parse_args()
    return run(args.config, args.configvar)



def run(config_file, overrides):
    # Parse the config files
    if 'HOME' in os.environ:
        home = os.environ['HOME']
    else:
        home = '~'

    # User settings
    settings_file = os.path.join(home, '.config', 'spiny.cfg')

    config = ConfigParser()
    config.read([settings_file, config_file, 'setup.cfg'])

    for override in overrides:
        if ':' not in override or '=' not in override:
            raise ValueError('%s is not a valid config variable. '
                             'It should be "section:variable=value"')
        section, rest = override.split(':', 1)
        option, value = rest.split('=', 1)
        if not config.has_section(section):
            config.add_section(section)
        config.set(section.strip(), option.strip(), value.strip())

    # Get the verified environments
    pythons = environment.get_pythons(config)

    # Install a virtualenv for each environment
    if config.has_option('spiny', 'venv_dir'):
        venv_dir = config.get('spiny', 'venv_dir')
    else:
        venv_dir = '.venv'
    venv_dir = os.path.abspath(venv_dir)
    envs = environment.get_environments(config)
    install_virtualenvs(envs, pythons, venv_dir)

    # Run commands
    if not config.has_option('spiny', 'test_commands'):
        commands = ['{python} setup.py test']
    else:
        commands = config.get('spiny', 'test_commands').splitlines()

    results = run_commands(envs, venv_dir, commands)

    # Done
    for env in envs:
        if results[env]:
            print("ERROR: Running tests under %s failed!" % env)
        else:
            print("       Running tests under %s suceeded." % env)

    return 1 if any(results.values()) else 0
