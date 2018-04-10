import click

from src.util import load_pickle, save_pickle


def link_dictionaries(d1, d2):
    """Link two dictionaries into a new dictionary

    The two dictionaries must have the same set of keys. If so, the resulting
    dict will map the values of the first dict into the values of the second
    dict.

    Examples:

        >>> d1 = {1: 2}
        >>> d2 = {1: 5}
        >>> link_dictionaries(d1, d2)
        {2: 5}

        >>> # when a key is not present in both
        >>> # it is ignored
        >>> d2 = {1: 5, -2: 0}
        >>> link_dictionaries(d1, d2)
        {2: 5}

    """
    keys = set(d1.keys()) & set(d2.keys())

    ret = {}
    for key in keys:
        ret[d1[key]] = d2[key]

    return ret


@click.command()
@click.argument('in-dict1', type=click.Path(exists=True))
@click.argument('in-dict2', type=click.Path(exists=True))
@click.argument('out-dict', type=click.Path(writable=True))
def CLI(in_dict1, in_dict2, out_dict):
    """Link two dictionaries into a new dictionary

    The new dictionary will be generated from the values of the first and
    second dictionary. These values will be linked by their keys.

    If there's a key that is present in one dictionary, but not in another, it
    will be ignored.

    \b
    Inputs:
        in-dict1 (pkl): The first dictionary.
        in-dict2 (pkl): The second dictionary.

    \b
    Outputs:
        out-dict (pkl): The resulting dictionary, combining values from dict1
            and dict2.
    """
    dict1 = load_pickle(in_dict1)
    dict2 = load_pickle(in_dict2)

    new_dict = link_dictionaries(dict1, dict2)
    save_pickle(out_dict, new_dict)


if __name__ == '__main__':
    CLI()
