import argparse
import logging
import multiprocessing
import os
import os.path
import pkg_resources
import sys

if sys.version_info < (3,):
    import subprocess32 as subprocess
    from ConfigParser import ConfigParser
else:
    import subprocess
    from configparser import ConfigParser

from spiny import environment, projectdata

__version__ = pkg_resources.require("spiny")[0].version

logger = logging.getLogger('spiny')

class Filter(object):
    """Only log messages that are non-empty."""

    def filter(self, record):
        return len(record.msg)


class LevelFormatter(logging.Formatter):
    """Formatter with a format per level"""
    def __init__(self, fmt=None, datefmt=None, level_formats=None):
        super(LevelFormatter, self).__init__(fmt, datefmt)
        if level_formats is None:
            level_formats = {}
        self._level_formats = level_formats
        self._default_format = fmt

    def format(self, record):
        self._fmt = self._level_formats.get(record.levelno, self._default_format)
        return super(LevelFormatter, self).format(record)


def setup_logging(verbose, quiet):

    verbosity = 2
    if verbose is not None:
        verbosity += verbose
    if quiet is not None:
        verbosity -= quiet

    verbosity = max((0, min(4, verbosity)))
    level = 50-(10*verbosity)

    # The levels can be:
    # 50: Only used for "Oups I failed" messages. -qq
    # 40: Quiet level. Should be used only by the final status message. -q
    # 30: Normal level. "I'm doing this now". Unexpected stderr outputs.
    # 20: Verbose level. All outputs, except when probing. -v
    # 10: Debug level. All outputs, detailed messages. -vv
    # As you notice, these correspone to the logging modules levels
    # CRITICAL, ERROR, WARNING, INFO and DEBUG, but those names
    # don't fit well here. Also, we want different formatting for
    # different levels. So:
    handler = logging.StreamHandler()
    handler.addFilter(Filter())
    formats = {30: '%(message)s', 40: '%(message)s'}
    handler.setFormatter(LevelFormatter('%(levelname)s:\n%(message)s',
                                        level_formats=formats))
    logger.setLevel(level)
    logger.addHandler(handler)


def run_all_tests(envnames, pythons, venv_dir, test_commands):
    """Run a list of commands in each virtualenv"""

    if not os.path.exists(venv_dir):
        os.mkdir(venv_dir)

    cpus = min(multiprocessing.cpu_count(), len(envnames))
    logger.log(20, "Using %s parallel processes" % cpus)
    pool = multiprocessing.Pool(processes=cpus)
    results = pool.map(run_tests, [(envname, pythons[envname], venv_dir, test_commands) for envname in envnames])

    return dict(zip(envnames, results))


def run_tests(args):
    envname, envdict, venv_dir, test_commands = args
    project_data = projectdata.get_data('.')

    requirements = []
    requirements.extend(project_data.get('install_requires', []))
    requirements.extend(project_data.get('setup_requires', []))
    requirements.extend(project_data.get('tests_require', []))
    requirements.extend(project_data.get('extras_require', {}).get('tests', []))
    dependency_links = project_data.get('dependency_links', [])

    exepath = envdict['path']
    envpath = os.path.join(venv_dir, envname)

    if envdict['virtualenv'] == 'internal':
        # Internal means use the virtualenv for the relevant Python
        command = [exepath, '-m', 'virtualenv', envpath]
    else:
        # External means use the virtualenv for the current Python
        command = [sys.executable, '-m', 'virtualenv',
                   '-p', exepath, envpath]

    logger.log(30, 'Install/update virtualenv for %s' %  envname)
    logger.log(10, 'Using command: %s' %  ' '.join(command))
    with subprocess.Popen(command,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE) as process:
        process.wait()
        logger.log(30, process.stderr.read())
        logger.log(20, process.stdout.read())
        if process.returncode != 0:
            # This failed somehow
            msg = "Installing/updating virtualenv for %s failed!" % envname
            logger.log(30, msg)
            return msg

    # Install dependencies:
    pip_path = os.path.join(envpath, 'bin', 'pip')
    parameters = '-f '.join(dependency_links).split()
    if envdict['python'] == 'Python' and envdict['version'] < '2.6': # Using 2.5 or worse
        parameters.append('--insecure')

    command = [pip_path] + parameters + ['install'] + requirements

    logger.log(10, 'Install dependencies with command: %s' %  ' '.join(command))
    with subprocess.Popen(command,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE) as process:
        process.wait()
        logger.log(30, process.stderr.read())
        logger.log(20, process.stdout.read())
        if process.returncode != 0:
            # This failed somehow
            msg = "Installing/updating dependencies for %s failed!" % envname
            logger.log(30, msg)
            return msg

    # Run tests:
    logger.log(30, 'Running tests for %s' %  envname)
    envpath = os.path.join(venv_dir, envname)
    python = os.path.join(envpath, 'bin', envname)
    for command in test_commands:
        command = command.strip().format(environment=envpath, python=python)
        logger.log(10, 'Using command: %s' %  command)
        with subprocess.Popen(command.split(),
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE) as process:
            process.wait()
            logger.log(30, process.stderr.read())
            logger.log(30, process.stdout.read())
            if process.returncode != 0:
                msg = "Tests failed for %s!" % envname
                return msg

    return None # Got None problems!


def main():
    parser = argparse.ArgumentParser(
        description='Run tests under several Python versions.',
        add_help=False
    )

    parser.add_argument(
        '-h',
        '--help',
        action='help',
        help='Show this help message and exit.')

    parser.add_argument(
        '--version',
        action='version',
        version=__version__,
        help='Show the version and exit.')

    parser.add_argument(
        '-c',
        '--config',
        action='store',
        default='spiny.cfg',
        metavar='<filename>',
        type=str,
        help='The config file to use. Defaults "to spiny.cfg".')

    parser.add_argument(
        '-e',
        '--envlist',
        action='store',
        metavar='<environments>',
        type=str,
        help='A list of environments to run, separated by commas.')

    parser.add_argument(
        '-v',
        '--verbose',
        action='count',
        help='Increases the output, -vv increases it even more.')

    parser.add_argument(
        '-q',
        '--quiet',
        action='count',
        help='Reduces output to only the run summary, -qq removes also that.')

    parser.add_argument(
        'configvar',
        action='store',
        type=str,
        nargs='*',
        metavar='<configvar>',
        help='Override a config variable by "section:variable=value" '
             'Example: "spiny:venv_dir=.venv"')

    args = parser.parse_args()

    setup_logging(args.verbose, args.quiet)

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

    # Run tests
    if not config.has_option('spiny', 'test_commands'):
        commands = ['{python} setup.py test']
    else:
        commands = config.get('spiny', 'test_commands').splitlines()

    results = run_all_tests(envs, pythons, venv_dir, commands)

    # Done
    for env in envs:
        if results.get(env):
            logger.log(40, "ERROR: " + results[env])
        else:
            logger.log(40, "       Running tests under %s suceeded." % env)

    return 1 if any(results.values()) else 0
