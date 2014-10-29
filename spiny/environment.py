import logging
import os
import os.path
import re
import string
import sys

if sys.version_info < (3,):
    import subprocess32 as subprocess
else:
    import subprocess

PYTHON_TROVE_RE = re.compile(b'''Programming Language :: Python :: (.*?)['"]''')
PYPY_VER_RE = re.compile(r'PyPy ([\d\.]*)')

logger = logging.getLogger('spiny')

def get_environments(conf):
    if conf.has_option('spiny', 'environments'):
        environments = conf.get('spiny', 'environments').split()
    else:
        with open('setup.py', 'rb') as setuppy:
            environments = ['python' + version for version in PYTHON_TROVE_RE.findall(setuppy.read())]

    # If "Python X" is specified and "Python X.Y" is also specified, skip "Python X"
    return [e for e in environments if not any([x.startswith(e) and len(x) >
                                                len( e) for x in environments])]


def python_info(fullpath):
    # Figure out the version of the Python exe
    logger.log(10, 'Getting Python version for %s' % fullpath)
    with subprocess.Popen([fullpath, '--version'],
                          stderr=subprocess.PIPE,
                          stdout=subprocess.PIPE) as process:
        process.wait()
        stderr = process.stderr.read()
        stdout = process.stdout.read()
        logger.log(10, stderr)
        logger.log(20, stdout)

        version_info = (stderr.strip() + stdout.strip()).decode('ascii', errors='ignore')
        pypy = PYPY_VER_RE.search(version_info)
        if pypy:
            python = 'PyPy'
            version = pypy.groups()[0]
        else:
            parts = version_info.split()
            if len(parts) != 2:
                raise EnvironmentError("Unkown Python interpreter at %s" % fullpath)
            python = parts[0]
            version = parts[1]

        version_tuple = version.split('.')

    # Return all valid environment names
    environment1 = '%s%s' % (python.lower(), version_tuple[0])
    environment2 = '%s.%s' % (environment1, version_tuple[1])
    environment3 = '%s.%s' % (environment2, version_tuple[2])

    return python, version, [environment1, environment2, environment3]


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
            if execname not in ('python', 'pypy', 'jython', 'ironpython'):
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

    logger.log(10, 'Checking for virtualenv: %s' %  ' '.join(command))
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
    logger.log(10, 'Trying local virtualenv: %s' %  ' '.join(command))
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

            p, v, envs = python_info(path)
            if python not in envs:
                raise EnvironmentError(
                    'Executable %s is not the given version %s' % (path, python))

            # The given python is OK, add it to the python env:
            pythons[python] = {'python': p,
                               'version': v,
                               'path': path}

            # Add the other envs for this particular python, if this is a higher version:
            for env in envs:
                if env not in pythons or pythons[env]['version'] < v:
                    pythons[env] = {'python': p,
                                    'version': v,
                                    'path': path}

    # Add the Python versions in the path for versions that are not specified:
    path = os.environ['PATH']
    for fullpath in list_pythons_on_path(path):

        python, version, envs = python_info(fullpath)
        for env in envs:
            if env not in pythons:
                pythons[env] = {'python': python,
                                'version': version,
                                'path': fullpath}

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
