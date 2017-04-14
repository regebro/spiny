from setuptools import setup, find_packages
import os.path
import sys

with open("README.rst") as infile:
   readme = infile.read()
with open(os.path.join("docs", "CHANGES.txt")) as infile:
   changes = infile.read()
long_desc = readme + '\n\n' + changes

setup(
    name='spiny',
    version='0.7.dev0',
    description='''Spiny will run your Python tests under multiple versions of Python''',
    long_description=long_desc,
    keywords=['development', 'tools', 'testing'],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Operating System :: Unix",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Topic :: Software Development :: Testing",
        ],
    packages=find_packages(),
    include_package_data=True,
    zip_safe=True,
    author='Lennart Regebro',
    author_email='regebro@gmail.com',
    url="https://github.com/regebro/spiny/",
    license='MIT',
    entry_points={
        'console_scripts': [
            'spiny = spiny.main:main',
        ]
    },
    test_suite='tests'
)
