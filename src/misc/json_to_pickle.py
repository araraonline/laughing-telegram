import click

from src.util import load_json, save_pickle


@click.command()
@click.argument('in-json', type=click.Path(exists=True))
@click.argument('out-pickle', type=click.Path(writable=True))
def CLI(in_json, out_pickle):
    """Converts a json file to pickle

    \b
    Inputs:
        in-json (json): The json file to convert.

    \b
    Outputs:
        out-pickle (pkl): The converted pickle file
    """
    obj = load_json(in_json)
    save_pickle(out_pickle, obj)


if __name__ == '__main__':
    CLI()
