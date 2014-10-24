Spiny
=====

Spiny Norman is a Hedgehog.

It's also a package that will run your Python tests under multiple versions of Python.
It's currently Alpha software, and just a test.

"Hey hang on!" I hear you say, "There's already Tox!" And you are right.
Spiny is my attempt to make a replacement for Tox that is less complex,
and fixes a couple of problems with Tox.

Most notably, with Spiny, Python does not have to be on the path, it can install versions
of Python other than the one your installed version of virtualenv happens to support,
and it does not always call setup.py.

Command line parameters
-----------------------

  usage: spiny [-h] [--config <filename>] [<configvar> [<configvar> ...]]

  Run tests under several Python versions

  positional arguments:
    <configvar>           Override a config variable by "section:variable=value"
                          Example: "spiny:venv_dir=.venv"

  optional arguments:
    -h, --help            show this help message and exit
    --config <filename>, -c <filename>
                          The config file to use. If not given it will look first
                          for spiny.cfg and if that not exists it will use setup.cfg.

Configuration files
-------------------

The configuration file for Spiny is by default called
Here is an example config, typically called ``spiny.cfg``::

  [spiny]
  environments = python2.7
                 python3.4
                 pypy2.4

  venv_dir = .venv

  test_commands = {python} setup.py test

All options are optional. If no environment list is found, the "Programming
Language :: Python :: <version>" classifiers from setup.py will be used.

You can have several lines of commands in test_commands.

You can also set up a personal custom config in ``~/.config/spiny.cfg``::

  [pythons]
  python2.6 = /pythons/python26/bin/python
  python2.7 = /pythons/python27/bin/python
  python3.3 = /pythons/python33/bin/python3
  python3.4 = /pythons/python34/bin/python3

The above is an example of how to configure which Pythons you want to use.
If you don't configure this, they have to be on the PATH.

You can in fact also add the ``[pythons]`` section in your projects ``spiny.cfg``,
but the usecase for that is very limited. Possibly if you are using custom
Pythons in your project. You can also add a ``[spiny]`` section to your personal
``spiny.cfg``, but that is not likely to be useful.

Todo
----

Things that desperately needs doing:

  * Run it under Python 3, PyPy, IronPython, Jython.

  * Add more logging (and a verbose parameter)

  * Make the tests run under itself

  * Makre tests run in parallell
