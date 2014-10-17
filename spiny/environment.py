import os
import os.path
import string
import subprocess


def python_envs(fullpath):
    # Figure out the version
    process = subprocess.Popen([fullpath, '--version'],
                               stderr=subprocess.PIPE,
                               stdout=subprocess.PIPE)
    stderr = process.stderr.read()
    stdout = process.stdout.read()
    version_info = stderr.strip() + stdout.strip()
    python, version = version_info.split()
    version_tuple = version.split('.')

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

            if fullpath in pythons.values():
                # We found this already
                continue

            python, version, envs = python_envs(fullpath)
            for env in envs:
                if env not in pythons:
                    pythons[env] = {'python': python,
                                    'version': version,
                                    'path': fullpath}

    return pythons


def verify_environment(conf):
    # Make sure we have the Python versions required:

    env_list = [x.strip() for x in
                conf.get('spiny', 'environments').split(',')]
    path = os.environ['PATH']
    pythons = list_pythons_on_path(path)

    if conf.has_section('pythons'):
        for python, path in conf.items('pythons'):
            if not os.access(path, os.X_OK):
                # Not executable
                raise EnvironmentError( '%s is not executable' % path)

            p, v, envs = python_envs(path)
            if python not in envs:
                raise EnvironmentError(
                    'Executable %s is not the given version %s' % (path, python))

            # The given python is OK, add it to the python env:
            pythons[python] = path

            # Add the other envs for this particular python, if they don't exist otherwise:
            for env in envs:
                if env not in pythons:
                    pythons[env] = path

    for env in env_list:
        if env not in pythons:
            raise EnvironmentError('Could not find an executable for %s' % env)
