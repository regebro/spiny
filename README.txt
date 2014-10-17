spiny
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

Here is an example config, typically called spiny.conf::

  [spiny]
  environments = python2.7
                 python28

And you can set up personal custom configs in ~/.config/spiny.conf::

  [pythons]
  python2.6 = /pythons/python26/bin/python
  python2.7 = /pythons/python27/bin/python
  python3.3 = /pythons/python33/bin/python3
  python3.4 = /pythons/python34/bin/python3

The above is an example of how to configure which Pythons you want to use.
If you don't configure this, they have to be on the PATH.
