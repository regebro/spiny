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


def run_all_tests(config):
    """Run a list of commands in each virtualenv"""

    # Get the location of environments.
    if config.has_option('spiny', 'venv-dir'):
        venv_dir = config.get('spiny', 'venv-dir')
    else:
        venv_dir = '.venv'
    venv_dir = os.path.abspath(venv_dir)

    # Get the list of environments to be used:
    pythons = environment.get_pythons(config)
    envnames = environment.get_environments(config)

    # Get the setup commands:
    if config.has_option('spiny', 'setup-commands'):
        setup_commands = config.get('spiny', 'setup-commands').splitlines()
    else:
        setup_commands = None

    # Get the test commands:
    if config.has_option('spiny', 'test-commands'):
        test_commands = config.get('spiny', 'test-commands').splitlines()
    else:
        test_commands = ['{python} setup.py test']

    if config.has_option('spiny', 'max-processes'):
        max_proc = int(config.get('spiny', 'max-processes'))
    else:
        max_proc = None

    # Get requirements from setup.py
    requirements = []
    if (config.has_option('spiny', 'use-setup-py') and
        config.get('spiny', 'use-setup-py').lower() in
        ['false', 'off', '0', 'no']):
        # Use of setup.py is disabled.
        dependency_links = []
    else:
        project_data = projectdata.get_data('.')
        requirements.extend(project_data.get('install_requires', []))
        requirements.extend(project_data.get('setup_requires', []))
        requirements.extend(project_data.get('tests_require', []))
        requirements.extend(project_data.get('extras_require', {}).get('tests', []))
        dependency_links = project_data.get('dependency_links', [])

    # Get even more requirements from requirements.txt.
    if (config.has_option('spiny', 'use-requirements-txt') and
        config.get('spiny', 'use-requirements-txt').lower() in
        ['false', 'off', '0', 'no']):
        # Use of requirements.txt is disabled.
        pass  # Yes, I want it like this, because it's clearer.
    else:
        if os.path.isfile('requirements.txt'):
            with open('requirements.txt', 'rt') as reqtxt:
                requirements.extend(reqtxt.readlines())

    if not os.path.exists(venv_dir):
        os.mkdir(venv_dir)

    cpus = min(multiprocessing.cpu_count(), len(envnames))
    if max_proc:
        cpus = min(cpus, max_proc)
    logger.log(20, "Using %s parallel processes" % cpus)
    pool = multiprocessing.Pool(processes=cpus)
    argslist = [(envname,
                 pythons[envname],
                 venv_dir,
                 setup_commands,
                 test_commands,
                 requirements,
                 dependency_links) for envname in envnames]
    results = pool.map(run_tests, argslist)

    return dict(zip(envnames, results))


def run_tests(args):
    envname, envdict, venv_dir, setup_commands, test_commands, requirements, dependency_links = args

    exepath = envdict['path']
    envpath = os.path.join(venv_dir, envname)
    project_dir = os.path.abspath(os.path.curdir)

    # Create a "profile"" of this virtualenv, include name, the python exe and requirements.
    venv_profile = '\n'.join([envname, exepath, '\n'.join(sorted(requirements))])
    # Check if there is an existing venv, and in that case read in it's profile:
    profile_path = os.path.join(envpath, '.spiny-profile')
    if os.path.exists(profile_path):
        with open(profile_path, 'rb') as profile:
            installed_profile = profile.read()
    else:
        installed_profile = ''

    if venv_profile != installed_profile:
        # We need to install the virtualenv or update the requirements.

        if not setup_commands:
            if envdict['virtualenv'] == 'internal':
                # Internal means use the virtualenv for the relevant Python
                setup_commands = [[exepath, '-m', 'virtualenv', '-v', envpath]]
            else:
                # External means use the virtualenv for the current Python
                setup_commands = [[sys.executable, '-m', 'virtualenv', '-v',
                                   '-p', exepath, envpath]]
        else:
            setup_commands = [command.split() for command in setup_commands]

        logger.log(30, 'Install/update virtualenv for %s' % envname)
        for command in setup_commands:
            logger.log(10, 'Using command: %s' % ' '.join(command))
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
        if envdict['python'] == 'Python' and envdict['version'] < '2.6':
            # Using 2.5 or worse means no SSL.
            parameters.append('--insecure')

        command = [pip_path] + parameters + ['install'] + requirements

        logger.log(10, 'Install dependencies with command: %s' % ' '.join(command))
        with subprocess.Popen(command,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE) as process:
            process.wait()
            logger.log(30, process.stderr.read())  # Log stderr only if verbose output.
            if process.returncode != 0:
                # This failed somehow.
                msg = "Installing/updating dependencies for %s failed!" % envname
                logger.log(30, msg)
                # pip has the error on stdout. Log it on normal level.
                logger.log(30, process.stdout.read())
                return msg
            else:
                # Log successful stdout only if output level is verbse.
                logger.log(20, process.stdout.read())

        # Save the venv information:
        with open(profile_path, 'wb') as profile:
            profile.write(venv_profile)

    # Run tests:
    logger.log(30, 'Running tests for %s' % envname)
    envpath = os.path.join(venv_dir, envname)
    python = os.path.join(envpath, 'bin', envdict['execname'])

    for command in test_commands:
        command = command.strip().format(envpath=envpath,
                                         python=python,
                                         project_dir=project_dir)
        logger.log(10, 'Using command: %s' % command)
        with subprocess.Popen(command.split(),
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE) as process:
            process.wait()
            logger.log(30, process.stderr.read())
            logger.log(30, process.stdout.read())
            if process.returncode != 0:
                msg = "Tests failed for %s!" % envname
                return msg

    return None


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
             'Example: "spiny:venv-dir=.venv"')

    args = parser.parse_args()

    setup_logging(args.verbose, args.quiet)

    if args.envlist:
        args.configvar.append('spiny:environments=' + args.envlist.replace(',', ' '))
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
                             'It should be "section:variable=value"' % override)
        section, rest = override.split(':', 1)
        option, value = rest.split('=', 1)
        if not config.has_section(section):
            config.add_section(section)
        config.set(section.strip(), option.strip(), value.strip())

    results = run_all_tests(config)

    # Done
    for env in sorted(results):
        if results.get(env):
            logger.log(40, "ERROR: " + results[env])
        else:
            logger.log(40, "       Running tests under %s suceeded." % env)

    return 1 if any(results.values()) else 0
