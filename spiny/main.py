import argparse
import os
import os.path

from spiny import environment

try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser

def main():
    parser = argparse.ArgumentParser(
        description='Frabble the foo and the bars')

    parser.add_argument('-c', action='store', nargs=1, default='spiny.conf', metavar='<filename>',
                        type=file, help='The config file to use. Defaults to "spiny.conf"')

    args = parser.parse_args()

    print args


def run(config_file):
    # Parse the config files
    if 'HOME' in os.environ:
        home = os.environ['HOME']
    else:
        home = '~'

    # User settings
    settings_file = os.path.join(home, '.config', 'spiny.conf')

    config = ConfigParser()
    config.read([config_file, settings_file])

    # Check that it's settings make sense
    environment.verify_environment(config)

    # Run virtualenvs.
    # Run the test commands

    pass
