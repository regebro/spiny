import logging
import os
import os.path
import re
import string
import sys

from distutils.version import LooseVersion

if sys.version_info < (3,):
    import subprocess32 as subprocess
else:
    import subprocess

PYTHON_TROVE_RE = re.compile(b'''Programming Language :: Python :: (.*?)( :: (.*?))?['"]''')
PYPY_VER_RE = re.compile(r'PyPy ([\d\.]*)')

logger = logging.getLogger('spiny')


def get_environments(conf):
    if conf.has_option('spiny', 'environments'):
        environments = conf.get('spiny', 'environments').split()
    else:
        with open('setup.py', 'rb') as setuppy:
            environments = []
            for match in PYTHON_TROVE_RE.findall(setuppy.read()):
                if match[2]:
                    env = match[2].lower()
                else:
                    env = 'python' + match[0]
                environments.append(env)

    # If "Python X" is specified and "Python X.Y" is also specified, skip "Python X"
    return [e for e in environments if not any([x.startswith(e) and len(x) >
                                                len(e) for x in environments])]


def python_info(fullpath):
    # Figure out the version of the Python exe
    logger.log(10, 'Getting Python version for %s' % fullpath)
    with subprocess.Popen([fullpath, '-V'],
                          stderr=subprocess.PIPE,
                          stdout=subprocess.PIPE) as process:
        process.wait()
        stderr = process.stderr.read()
        stdout = process.stdout.read()
        logger.log(10, stderr)
        logger.log(10, stdout)

        # Python 3.4 and Jython prints it on stdout, all others on stderr.
        if stdout:
            version_string = stdout
        else:
            version_string = stderr

        version_info = version_string.strip().decode('ascii', errors='ignore')
        parts = version_info.split()
        python = parts[0]
        version = parts[1]

        pypy = PYPY_VER_RE.search(version_info)
        if pypy:
            if version[0] == '3':
                # This is a Python 3 compatible version:
                python = 'PyPy3'
            else:
                python = 'PyPy'
            version = pypy.groups()[0]

    # Return all valid environment names
    env_version = LooseVersion(version).version
    environment = ['%s' % python.lower(),
                   '%s%s' % (python.lower(), env_version[0])]
    for v in env_version[1:]:
        environment.append('%s.%s' % (environment[-1], v))

    return {'python': python,
            'version': version,
            'path': fullpath,
            'execname': os.path.split(fullpath)[-1],
            'environments': environment}


def list_pythons_on_path(path):
    """Finds all Python versions in the list of directory paths given"""
    pythons = {}
    for p in path.split(os.pathsep):
        try:
            files = os.listdir(p)
        except OSError:
            # Path does not exist
            continue

        for filename in files:
            execname = ''.join(x for x in filename.lower()
                               if x in string.ascii_lowercase)
            if execname not in ('python', 'pypy', 'jython', 'ipyexe'):
                continue

            # Find the executable
            fullpath = os.path.realpath(os.path.join(p, filename))
            if not os.access(fullpath, os.X_OK):
                # Not executable
                continue

            if fullpath in [x['path'] for x in pythons.values()]:
                # We found this already
                continue

            yield fullpath


def has_virtualenv(exepath):
    command = [exepath, '-m', 'virtualenv']

    logger.log(10, 'Checking for virtualenv: %s' % ' '.join(command))
    with subprocess.Popen(command,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE) as process:
        process.wait()
        stderr = process.stderr.read()
        stdout = process.stdout.read()
        logger.log(10, stderr)
        logger.log(10, stdout)

        return not (process.returncode == 1 or stderr)


def can_use_current_virtualenv(exepath):
    command = [sys.executable, '-m', 'virtualenv', '-p', exepath]
    logger.log(10, 'Trying local virtualenv: %s' % ' '.join(command))
    with subprocess.Popen(command,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE) as process:
        process.wait()
        stderr = process.stderr.read()
        stdout = process.stdout.read()
        logger.log(10, stderr)
        logger.log(10, stdout)

        # Different versions of virtualenv seem to deal with this error
        # slightly differently. Test for all of it.
        return not (process.returncode in [1, 101] or stderr or
                    b'ERROR:' in stdout)


def get_pythons(conf):
    pythons = {}

    # Make sure we have the Python versions required:
    if conf.has_section('pythons'):
        for python, path in conf.items('pythons'):
            if not os.access(path, os.X_OK):
                # Not executable
                raise EnvironmentError('%s is not executable' % path)

            info = python_info(path)
            if python not in info['environments']:
                raise EnvironmentError(
                    'Executable %s is not the given version %s' % (path, python))

            # Add the other envs for this particular python, if this is a higher version:
            for env in info['environments']:
                if env not in pythons or pythons[env]['version'] < info['version']:
                    pythons[env] = info

    # Add the Python versions in the path for versions that are not specified:
    path = os.environ['PATH']
    for fullpath in list_pythons_on_path(path):

        info = python_info(fullpath)
        for env in info['environments']:
            if env not in pythons:
                pythons[env] = info

    # Check that the specified environments have a functioning virtualenv:
    env_list = get_environments(conf)
    for env in env_list:
        if env not in pythons:
            raise EnvironmentError('Could not find an executable for %s' % env)

        exepath = pythons[env]['path']
        if not has_virtualenv(exepath):
            # Something went wrong. Most likely there is no virtualenv module
            # installed for this Python. Try with the current Python.
            if not can_use_current_virtualenv(exepath):
                # That didn't work either.
                raise EnvironmentError(
                    "The Python at %s does not have virtualenv installed, and the "
                    "virtualenv for %s could not install that Python version. "
                    "To solve this, install virtualenv for %s" % (
                        exepath, sys.executable, exepath))
            else:
                pythons[env]['virtualenv'] = 'external'

        else:
            pythons[env]['virtualenv'] = 'internal'

    return pythons
