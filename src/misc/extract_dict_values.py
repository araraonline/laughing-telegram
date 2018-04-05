import click

from src.util import load_pickle, save_pickle


@click.command()
@click.argument('in-dict', type=click.Path(exists=True))
@click.argument('out-list', type=click.Path(writable=True))
def CLI(in_dict, out_list):
    """Extracts the values from a dictionary

    \b
    Inputs:
        in-dict (pkl): The dictionary whose values will be extracted.

    \b
    Outputs:
        out-list (pkl): The list of values from the input dictionary.
    """
    d = load_pickle(in_dict)
    l = list(d.values())
    save_pickle(out_list, l)


if __name__ == '__main__':
    CLI()
