import logging
import os
import os.path
import pickle
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
                    if env == 'cpython':
                        # That you support CPython is assumed, skip this.
                        continue
                else:
                    env = 'python' + str(match[0].decode('ascii', 'ignore'))
                environments.append(env)

    # If "Python X" is specified and "Python X.Y" is also specified, skip "Python X"
    return [e for e in environments if not any([x.startswith(e) and len(x) >
                                                len(e) for x in environments])]


def python_info(fullpath, cache):
    # Figure out the version of the Python exe
    logger.log(10, 'Getting Python version for %s' % fullpath)
    if fullpath in cache:
        mtime = os.stat(fullpath).st_mtime
        if mtime == cache[fullpath]['mtime']:
            return cache[fullpath]

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

        version_info = version_string.strip().decode('ascii', 'ignore')
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

    info = {'python': python,
            'version': version,
            'path': fullpath,
            'execname': os.path.split(fullpath)[-1],
            'environments': environment,
            'mtime': os.stat(fullpath).st_mtime}

    cache[fullpath] = info
    return info


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
    # Open cache file, if it exists:
    if conf.has_option('spiny', 'cache-file'):
        cache_file = conf.get('spiny', 'cache-file')
    else:
        cache_file = '~/.cache/spiny/pythons.cache'

    cache_file = os.path.expanduser(cache_file)

    cache = {}
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'rb') as infile:
                cache = pickle.load(infile)
        except (EOFError, OSError) as e:
            logger.log(30, "Could not load info cache from %s" % cache_file, exc_info=1)

    pythons = {}

    # Make sure we have the Python versions required:
    if conf.has_section('pythons'):
        for python, path in conf.items('pythons'):
            if not os.access(path, os.X_OK):
                # Not executable
                raise EnvironmentError('%s is not executable' % path)

            info = python_info(path, cache)
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
        info = python_info(fullpath, cache)
        for env in info['environments']:
            if env not in pythons:
                pythons[env] = info

    # Check that the specified environments have a functioning virtualenv:
    env_list = get_environments(conf)
    for env in env_list:
        if env not in pythons:
            logger.log(40, 'ERROR: Could not find an executable for %s' % env)
            continue

        if 'virtualenv' in pythons[env]:
            # We have already checked the virtualenv for this.
            continue

        if pythons[env]['version'] < u'2.4':
            # Python 2.3 and lower doesn't have virtualenv
            pythons[env]['virtualenv'] = 'unsupported'
            continue

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

    try:
        cache_dir = os.path.split(cache_file)[0]
        if not os.path.isdir(cache_dir):
            os.mkdir(cache_dir)

        with open(cache_file, 'wb') as outfile:
            cache = pickle.dump(cache, outfile, protocol=2)
    except OSError as e:
        logger.log(30, "Could not save Python info cache file %s" % cache_file, exc_info=1)

    return pythons
