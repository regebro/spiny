from setuptools import setup, find_packages
import os.path

readme = open("README.rst").read()
changes = open(os.path.join("docs", "CHANGES.txt")).read()
long_desc = readme + '\n\n' + changes

setup(
    name='spiny',
    version='0.2',
    description='''Spiny will run your Python tests under multiple versions of Python''',
    long_description=long_desc,
    keywords=['development', 'tools', 'testing'],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Operating System :: Unix",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Topic :: Software Development :: Testing",
        ],
    packages=find_packages(),
    include_package_data=True,
    zip_safe=True,
    author='Lennart Regebro',
    author_email='regebro@gmail.com',
    url="https://github.com/regebro/spiny/",
    license='MIT',
    install_requires=[],
    entry_points={
        'console_scripts': [
            'spiny = spiny.main:main',
        ]
    },
    test_suite='tests'
)
