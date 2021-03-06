# Extracts information from a project that has a distutils setup.py file.
import os
import sys
import string
import logging


def parse_version(version):
    vmap = {'a': 'alpha', 'b': 'beta', 'c': 'candidate'}
    res = []
    version = list(reversed(version))
    v = ''
    while version:
        x = version.pop()
        if x in string.digits:
            v += x
            continue
        else:
            res.append(int(v))
            if v in vmap:
                res.append(vmap[v])
            elif v == ' ':
                break  # Nothing more after the space

    if len(res) == '3':
        res.extend(['final', 0])

    return tuple(res)


class FakeContext(object):

    def __init__(self, path):
        self._path = path

    def __enter__(self):
        self._old_path = os.path.abspath(os.curdir)
        if self._old_path in sys.path:
            sys.path.remove(self._old_path)
        os.chdir(self._path)

        if self._path not in sys.path:
            sys.path.insert(0, self._path)
            self._path_appended = True
        else:
            self._path_appended = False

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._path_appended:
            sys.path.remove(self._path)
        sys.path.append(self._old_path)

        os.chdir(self._old_path)


class SetupMonkey(object):

    def __init__(self, python_version=None):
        self.python_version = python_version
        self._old_python_version = None

    def distutils_setup_replacement(self, **kw):
        self._kw = kw
        self._kw['_setuptools'] = False

    def setuptools_setup_replacement(self, **kw):
        self._kw = kw
        self._kw['_setuptools'] = True

    def get_data(self):
        return self._kw

    def __enter__(self):
        import distutils.core
        self._distutils_setup = distutils.core.setup
        distutils.core.setup = self.distutils_setup_replacement

        try:
            import setuptools
            self._setuptools_setup = setuptools.setup
            setuptools.setup = self.setuptools_setup_replacement
        except ImportError:
            self._setuptools_setup = None

        self._kw = {}

        if self.python_version is not None:
            # If setup.py checks the Python version, we have to trick it
            # that we are running with the version that we'll run the
            # tests with, and not the version we really are using.
            self._old_python_version = sys.version, sys.version_info
            sys.version = self.python_version
            sys.version_info = parse_version(self.python_version)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        import distutils.core
        distutils.core.setup = self._distutils_setup
        if self._setuptools_setup is not None:
            import setuptools
            setuptools.setup = self._setuptools_setup

        if self._old_python_version is not None:
            sys.version, sys.version_info = self._old_python_version


def _specified_versions(data):
    classifiers = data.get('classifiers', [])
    for classifier in classifiers:
        parts = [p.strip() for p in classifier.split('::')]
        if parts[0] == 'Programming Language' and parts[1] == 'Python':
            if len(parts) == 2:
                # Specified Python, but no version.
                continue
            version = parts[2]
            try:
                int(version)
                # This is just specifying 2 or 3, not which version
                continue
            except ValueError:
                pass
            try:
                float(version)
                # This version is good!
                yield version
            except ValueError:
                # Not a proper Python version
                continue


def get_data(path, python_version=None):
    """
    Returns data from a package directory.
    'path' should be an absolute path.
    """
    # Run the imported setup to get the metadata.
    with FakeContext(path):
        with SetupMonkey(python_version) as sm:
            try:
                import setup
                metadata = sm.get_data()

                if not metadata:
                    # This may be a module, like twisted, that only runs setup()
                    # when setup.py is called as the main script. In that case it
                    # often has a main() script to call instead. Try that.
                    try:
                        setup.main()
                    except TypeError:  # OK, so it's twisted.
                        try:
                            setup.main([])
                        except TypeError:
                            pass  # OK, not twisted, then.
                    except AttributeError:
                        pass  # No, no main.

                    metadata = sm.get_data()
                del sys.modules['setup']
            except ImportError as e:
                # Either there is no setup py, or it's broken.
                logging.exception(e)
                metadata = {}

        # No data found
        if not metadata:
            return {}

    return metadata

if __name__ == '__main__':
    import json
    import sys
    path = sys.argv[1]
    print(json.dumps(get_data(path)))
