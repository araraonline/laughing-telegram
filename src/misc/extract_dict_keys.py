import click

from src.util import load_pickle, save_pickle


@click.command()
@click.argument('in-dict', type=click.Path(exists=True))
@click.argument('out-list', type=click.Path(writable=True))
def CLI(in_dict, out_list):
    """Extracts the keys from a dictionary

    \b
    Inputs:
        in-dict (pkl): The dictionary whose keys will be extracted.

    \b
    Outputs:
        out-list (pkl): The list of keys from the input dictionary.
    """
    d = load_pickle(in_dict)
    l = list(d.keys())
    save_pickle(out_list, l)


if __name__ == '__main__':
    CLI()
