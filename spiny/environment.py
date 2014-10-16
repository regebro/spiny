import os
import os.path
import string
import subprocess

def list_pythons_on_path(paths):
    """Finds all Python versions in the list of directory paths given"""
    pythons = {}
    for path in paths:
        try:
            files = os.listdir(path)
        except OSError:
            # Path does not exist
            continue

        for filename in files:
            execname = ''.join(x for x in filename.lower() if x in string.ascii_lowercase)
            if execname not in ('python', 'pypy', 'jython', 'ironpython'):
                continue

            # Find the executable
            fullpath = os.path.realpath(os.path.join(path, filename))

            if fullpath in pythons.values():
                # We found this already
                continue

            if not os.access(fullpath, os.X_OK):
                # Not executable
                continue

            # Figure out the version
            process = subprocess.Popen([fullpath, '--version'], stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            stderr = process.stderr.read()
            stdout = process.stdout.read()
            version_info = stderr.strip() + stdout.strip()
            python, version = version_info.split()
            version_tuple = version.split('.')
            environment1 = '%s%s' % (python.lower(), version_tuple[0])
            environment2 = '%s.%s' % (environment1, version_tuple[1])
            environment3 = '%s.%s' % (environment2, version_tuple[2])
            for env in (environment1, environment2, environment3):
                if not env in pythons:
                    pythons[env] = {'python': python, 'version': version, 'path': fullpath}

    return pythons


def verify_environment(conf):
    # Make sure we have the Python versions required:

    env_list = [x.strip() for x in conf.get('spiny', 'environments').split(',')]
    paths = os.environ['PATH'].split(os.pathsep)
    pythons = list_pythons_on_path(paths)

    for env in env_list:
        if env not in pythons:
            raise EnvironmentError('Could not find an executable for %s' % env)

