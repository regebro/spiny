Spiny
=====

Spiny Norman is a Hedgehog.

It's also a package that will run your Python tests under multiple versions
of Python.

"Hey hang on!" I hear you say, "There's already Tox!" And you are right.
Spiny is my attempt to look into the problem space tox covers to make
something that is less complex, and fixes a couple of problems with Tox.

Most notably, with Spiny, Python does not have to be on the path, it can
install versions of Python other than the one your installed version of
virtualenv happens to support, and it does not always call setup.py.
It also will run the tests in parallel.

Major feature: For the common use case it needs no configuration.

There is no guarantee that Spiny's features will not end up in Tox.


Command line parameters
-----------------------

You run Spiny from the root of the Python project that you want to test,
ie the direectory that has the ``setup.py`` file.

The command line parameters are:

  usage: spiny [-h] [--version] [-c <filename>] [-e <environments>] [-v] [-q]
               [<configvar> [<configvar> ...]]

  Run tests under several Python versions.

  positional arguments:
    <configvar>           Override a config variable by "section:variable=value"
                          Example: "spiny:venv-dir=.venv"

  optional arguments:
    -h, --help            Show this help message and exit.
    --version             Show the version and exit.
    -c <filename>, --config <filename>
                          The config file to use. Defaults "to spiny.cfg".
    -e <environments>, --envlist <environments>
                          A list of environments to run, separated by commas.
    -v, --verbose         Increases the output, -vv increases it even more.
    -q, --quiet           Reduces output to only the run summary, -qq removes
                          also that.


Version support
---------------

Spiny can be run under Python 2.6, 2.7, 3.3 and 3.4. It can also be run under
PyPy, PyPy3 and Jython.

It can run tests under a much wider range of Python versions, this has been tested
with Python 2.4, 2.5, 3.1 and 3.2 in addition to the above Python versions.

IronPython is supported in theory, but I can't get virtualenv working with
IronPython. Other Python implementations are not tested. If one doesn't work,
you are welcome to raise an issue and I can look into it.


Configuration files
-------------------

Spiny does not typically need a configuration file. It will instead look at
your ``setup.py`` and find out what Python versions you module supports, and
run the tests with those versions.

You declare version support with classifiers, like this::

  setup(
      ...
      classifiers=[
          ...
          "Programming Language :: Python",
          "Programming Language :: Python :: 2.6",
          "Programming Language :: Python :: 2.7",
          "Programming Language :: Python :: 3.3",
          "Programming Language :: Python :: 3.4",
          "Programming Language :: Python :: Implementation :: PyPy",
          ...
          ],
      ...
  )

With these classifiers, Spiny will run the tests under Python 2.6, 2.7, 3.3,
3.4 and also under PyPy.

You can configure Spiny explicitly on a configuration basis. You can add a
``spiny.cfg`` located in the project root, or you can add the configuration
to the projects ``setup.cfg``.

You can also have a personal configuration file in ``~/.config/spiny.cfg``
whose configuration options will be valid for all projects.

Under the ``[spiny]`` section the
following configuration options are supported:

  * **environments**: A whitespace separated list of Python and Python versions.

  * **venv-dir**: The name of the directory to install virtualenvs in.
    Defaults to ``.venv``.

  * **max-processes**: The maxiumum of concurrent processes to run tests with.
    Defaults to the number of CPU's you have.

  * **test-commands**: The commands used to run the tests. You can have
    several lines of commands. Defaults to ``{envpython} setup.py test``. There
    are a few variables that you can use in the commands that will be replaced:

    * ``{envpython}`` will be replaced with the full path to the Python
      executable in the virtualenv

    * ``{basepython}`` will be replaced with the full path to the Python
      executable the virtualenv is created from

    * ``{envdir}`` will be replaced with the full path to the virtualenv
      directory.

    * ``{projectdir}`` will be replaced with the full path to the directory
      of the Python project (ie, the current directory)

  * **setup-commands**: The commands used to create the virtualenv. The default
    for this varies, but it boils down to ``{envpython} -m virtualenv {envdir}``.

  * **use-setup-py**: If requirements data from ``setup.py`` should be used to
    gather requirements. This means ``setup.py`` needs to exist, and be
    executable without side-effects. Defaults to ``true``.

  * **use-requirements-txt**: If requirements data from ``requiremenets.txt``
    should be used to gather requirements. Defaults to ``true``.

  * **changedir**: A directory to change to before running the tests.
    Variables from test-commands are usable.


Example::

  [spiny]
  environments = python2.7
                 python3.4
                 pypy2.4

  venv-dir = .venv

  test-commands = {envpython} something.py magic
                  {envpython} setup.py test

  max-processes = 3

There is also a ``[pythons]`` section, which defines up the paths to the various
executables, per environment::

  [pythons]
  python2.6 = /pythons/python26/bin/python
  python2.7 = /pythons/python27/bin/python
  python3.3 = /pythons/python33/bin/python3
  python3.4 = /pythons/python34/bin/python3

If you don't configure this, the executables that are on the PATH will be used.

This doesn't make much sense to have in the projects ``spiny.cfg``,
as each person who runs the tests are likely to have differing Python installs.
However, this does make a lot of sense to have in the personal configuration file.

You can add the ``[pythons]`` section in your projects ``spiny.cfg``, but the
usecase for that is very limited. Possibly if you are using custom Pythons in
your project.

``max-processes`` also is reasonable in your personal file, if you for
example have very long-running tests, and you want to keep a CPU free, for
example for browing the web while the tests run. It also makes sense in a
project file if your tests use a lot of memory, to avoid running out of
memory.

``environments`` and ``test-commands`` only make sense per configuration and
not in the personal file. However, no checks for this are done, so you can
add them there if you want to, but the results are unlikely to be practical.


Todo
----

Things that needs doing:

  * Make the tests run under itself.

  * Figure out how to run coverage on things run by subprocesses.

  * Add commands per environment, enabling things like a pep8 environment
    that checks for pep8 compliance, etc.

  * Windows support. Maybe.
