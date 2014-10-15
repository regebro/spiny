import argparse

def main():
    parser = argparse.ArgumentParser(
        description='Frabble the foo and the bars')

    parser.add_argument('-c', action='store', nargs=1, default='spiny.ini', metavar='<filename>',
                        type=file, help='The config file to use. Defaults to "spiny.ini"')

    args = parser.parse_args()

    print args


def run(config_file):
    pass