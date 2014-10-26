import os
import os.path
import re
import string
import subprocess
import sys

PYTHON_RE = re.compile(b'''Programming Language :: Python :: (.*?)['"]''')


def get_environments(conf):
    if conf.has_option('spiny', 'environments'):
        environments = conf.get('spiny', 'environments').split()
    else:
        with open('setup.py', 'rb') as setuppy:
            environments = ['python' + version for version in PYTHON_RE.findall(setuppy.read())]

    # If "Python X" is specified and "Python X.Y" is also specified, skip "Python X"
    return [e for e in environments if not any([x.startswith(e) and len(x) >
                                                len( e) for x in environments])]


def python_info(fullpath):
    # Figure out the version of the Python exe
    process = subprocess.Popen([fullpath, '--version'],
                               stderr=subprocess.PIPE,
                               stdout=subprocess.PIPE)
    stderr = process.stderr.read()
    stdout = process.stdout.read()
    version_info = stderr.strip() + stdout.strip()
    python, version = version_info.split()
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

    env_list = get_environments(conf)
    for env in env_list:
        if env not in pythons:
            raise EnvironmentError('Could not find an executable for %s' % env)

        exepath = pythons[env]['path']
        process = subprocess.Popen([exepath, '-m', 'virtualenv'],
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        process.wait()
        if process.returncode == 1 or process.stderr.read():
            # Something went wrong. Most likely there is no virtualenv module
            # installed for this Python. Try with the current Python.
            # TODO: log warnings
            process = subprocess.Popen([sys.executable,
                                        '-m', 'virtualenv',
                                        '-p', exepath],
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)
            process.wait()
            # Different versions of virtualenv seem to deal with this error
            # slightly differently. Test for all of it.
            if (process.returncode in [1, 101] or process.stderr.read() or
                'ERROR:' in process.stdout.read()):
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
