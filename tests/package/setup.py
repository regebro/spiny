from setuptools import setup, find_packages

setup(
    name='spiny test package',
    version='1.0',
    description='''This is the package whose tests the spiny tests test.''',
    packages=find_packages(),
    author='Lennart Regebro',
    author_email='regebro@gmail.com',
    url="https://github.com/regebro/spiny/",
    license='MIT',
    install_requires=[],
    test_suite='tests'
)
