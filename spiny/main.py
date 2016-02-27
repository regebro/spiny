import argparse
import logging
import multiprocessing
import os
import os.path
import pkg_resources
import signal
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
    if not envnames:
        print("You must specify which Python environments to run tests under, "
              "either in setup.py or with the --envlist argument.")
        sys.exit(1)

    # Get the setup commands:
    if config.has_option('spiny', 'setup-commands'):
        setup_commands = filter(None, config.get('spiny', 'setup-commands').splitlines())
    else:
        setup_commands = None

    # Get the test commands:
    if config.has_option('spiny', 'test-commands'):
        test_commands = filter(None, config.get('spiny', 'test-commands').splitlines())
    else:
        test_commands = ['{envpython} setup.py test']

    if config.has_option('spiny', 'max-processes'):
        max_proc = int(config.get('spiny', 'max-processes'))
    else:
        max_proc = None

    # Get requirements from requirements.txt.
    requirements = []
    if not (config.has_option('spiny', 'use-requirements-txt') and
            config.get('spiny', 'use-requirements-txt').lower() in
            ['false', 'off', '0', 'no']):
        if os.path.isfile('requirements.txt'):
            with open('requirements.txt', 'rt') as reqtxt:
                requirements.extend(reqtxt.readlines())

    if (config.has_option('spiny', 'use-setup-py') and
        config.get('spiny', 'use-setup-py').lower() in
        ['false', 'off', '0', 'no']):
        # Use of setup.py is disabled.
        use_setup = False
    else:
        use_setup = True

    if config.has_option('spiny', 'changedir'):
        curdir = config.get('spiny', 'changedir')
    else:
        curdir = None

    if not os.path.exists(venv_dir):
        os.mkdir(venv_dir)

    projectdir = os.path.abspath(os.path.curdir)

    cpus = min(multiprocessing.cpu_count(), len(envnames))
    if max_proc:
        cpus = min(cpus, max_proc)

    executes = []
    skips = []
    argslist = []
    for envname in envnames:
        if envname in pythons:
            executes.append(envname)

            # Get requirements from setup.py
            reqs = requirements[:]
            if use_setup:
                project_data = projectdata.get_data('.', pythons[envname]['version'])
                reqs.extend(project_data.get('install_requires', []))
                reqs.extend(project_data.get('setup_requires', []))
                reqs.extend(project_data.get('tests_require', []))
                reqs.extend(project_data.get('extras_require', {}).get('tests', []))
                dependency_links = project_data.get('dependency_links', [])
            else:
                # Use of setup.py is disabled.
                dependency_links = []

            arguments = (envname,
                         pythons[envname],
                         venv_dir,
                         setup_commands,
                         test_commands,
                         reqs,
                         dependency_links,
                         projectdir,
                         curdir)
            argslist.append(arguments)
        else:
            skips.append(envname)

    all_reqs = [args[5] for args in argslist]
    for req in all_reqs:
        if req != all_reqs[0]:
            # There are different requirements for different versions.
            # Then we can't run the tests in parallell.
            cpus = 1
            logger.log(30, "Version dependent requirements detected, "
                           "not using parallelism.")
            break

    logger.log(20, "Using %s parallel processes" % cpus)
    pool = multiprocessing.Pool(processes=cpus)
    results = pool.map(run_tests, argslist)
    results = dict(zip(executes, results))
    for envname in skips:
        results[envname] = 'Error: Skipped %s' % envname

    return results


def run_tests(args):
    try:
        (envname, envdict, venv_dir, setup_commands, test_commands,
         requirements, dependency_links, projectdir, curdir) = args

        exepath = envdict['path']  # Actual Python exe
        if envdict['virtualenv'] == 'unsupported':
            # Python 2.3 or earlier (or otherwise)
            python = envdict['path']
            envdir = os.path.dirname(os.path.dirname(python))
        else:
            envdir = os.path.join(venv_dir, envname)  # virtualenv dir
            python = os.path.join(envdir, 'bin', envdict['execname'])  # Virtualenv python

        env_parameters = {
            'basepython': exepath,
            'envdir': envdir,
            'envpython': python,
            'projectdir': projectdir,
        }

        # Expand the current directory
        if curdir is not None:
            curdir = curdir.format(**env_parameters)
        else:
            curdir = projectdir

        # Create a "profile"" of this virtualenv, include name, the python exe and requirements.
        venv_profile = '\n'.join([envname, exepath, '\n'.join(sorted(requirements))])
        # Check if there is an existing venv, and in that case read in it's profile:
        profile_path = os.path.join(envdir, '.spiny-profile')
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
                    venvexe = exepath
                elif envdict['virtualenv'] == 'external':
                    # External means use the virtualenv for the current Python
                    venvexe = sys.executable
                if envdict['virtualenv'] == 'unsupported':
                    # No virtualenv
                    setup_commands = [[]]
                else:
                    setup_commands = [[venvexe, '-m', 'virtualenv', '-v',
                                       '-p', exepath, envdir]]

            else:
                setup_commands = [command.format(**env_parameters).split() for command in setup_commands]

            logger.log(30, 'Install/update virtualenv for %s' % envname)
            for command in setup_commands:

                # Switch to curdir, if it exists.
                if curdir is not None and os.path.isdir(curdir):
                    os.chdir(curdir)

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

            if requirements:
                # Install dependencies:
                pip_path = os.path.join(envdir, 'bin', 'pip')
                parameters = '-f '.join(dependency_links).split()
                parameters.append('-q')
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
            with open(profile_path, 'wt') as profile:
                profile.write(venv_profile)

        # Run tests:
        logger.log(30, 'Running tests for %s' % envname)

        for command in test_commands:
            command = command.strip().format(**env_parameters)
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

    except KeyboardInterrupt:
        return "Tests interrupted by CTRL-C"


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
