import click

from src.util import load_pickle, save_pickle


@click.command()
@click.argument('in-loteca-matches', type=click.Path(exists=True))
@click.argument('out-loteca-matches', type=click.Path(writable=True))
def CLI(in_loteca_matches, out_loteca_matches):
    """Process the loteca matches

    Right now, all this function will do is remove the matches for rounds we
    are not intereseted in.

    \b
    Inputs:
        loteca-matches (pkl): A pandas DataFrame with the preprocessed loteca
            matches.

    \b
    Outputs:
        loteca-matches (pkl): A pandas DataFrame with the processed loteca
            matches.
    """
    df = load_pickle(in_loteca_matches)

    # before round 366, we have no revenue information
    df = df[df.roundno >= 366]

    save_pickle(out_loteca_matches, df)


if __name__ == '__main__':
    CLI()
