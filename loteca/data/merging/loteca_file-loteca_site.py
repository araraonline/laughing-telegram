import click
import pandas as pd

@click.command()
@click.argument('file_loc', type=click.Path(exists=True))
@click.argument('site_loc', type=click.Path(exists=True))
@click.argument('output_loc', type=click.Path(writable=True))
def merge(file_loc, site_loc, output_loc):
    file_df = pd.read_pickle(file_loc)
    site_df = pd.read_pickle(site_loc)
    df = file_df.join(site_df.drop(columns=['date']))
    df.to_pickle(output_loc)

if __name__ == '__main__':
    merge()
