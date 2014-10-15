from setuptools import setup, find_packages
import os.path

readme = open("README.txt").read()
changes = open(os.path.join("docs", "CHANGES.txt")).read()
long_desc = readme + '\n\n' + changes

setup(
    name='spiny',
    version='1.0dev0',
    description='''Not yet''',
    long_description=long_desc,
    classifiers=[
        "Development Status :: 1 - Planning",
        "Operating System :: Unix",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.4",
        "Topic :: Software Development :: Testing",
        ],
    packages=find_packages(),
    include_package_data=True,
    zip_safe=True,
    author='Lennart Regebro',
    author_email='laurence@lrowe.co.uk',
    url="https://github.com/regebro/spiny/",
    license='MIT',
    install_requires=[],
    entry_points = {
        'console_scripts': [
            'spiny = spiny.main:main',
        ]
    },
    test_suite='tests'
)
