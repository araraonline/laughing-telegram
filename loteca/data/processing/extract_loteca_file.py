import pickle
import pandas as pd
import parsel
import click


def _read_int(x):
    try: 
        return int(x)
    except TypeError: 
        return

def _read_float(x):
        if x == ' - ': 
            return None
        return float(x.replace('.', '').replace(',', '.'))  
    
def read_htm(filepath, encoding=None):
    with open(filepath, encoding=encoding) as fp:
        return fp.read()

def extract_table(filepath):
    """Given a filepath, extract all the data from the table
    in it and return a tuple:    
     - A DataFrame containing all the information that was on the table
     - A list of list of cities, correponding to the winners of different rounds
    """
    
    ##################################
    ## retrieve content
    
    body = read_htm(filepath, encoding='windows-1252')
    selector = parsel.Selector(text=body)
    
    
    ##################################
    ## extract data from the big table    
    
    rows = selector.css('tr')
    header = rows[0]
    rows = rows[1:]

    columns = header.css('font::text').extract()

    i = 0  # row index
    total = 0  # total no of rows left for this round

    # data holders
    all_data = []
    all_cities = []
    all_states = []

    # temporary holders
    cities = []
    states = []

    while i < len(rows):
        row = rows[i]   
        if total == 0:        
            data = []
            cities = []
            states = []
            for cell_no, cell in enumerate(row.xpath('td')):
                if cell_no == 3:             
                    try:
                        cities.append(cell.xpath('text()').extract_first().strip())
                    except AttributeError:
                        pass
                elif cell_no == 4:
                    states.append(cell.xpath('text()').extract_first().strip())
                else:
                    data.append(cell.xpath('text()').extract_first())
            total = int(row.xpath('td/@rowspan').extract_first())       
        else:
            for cell_no, cell in enumerate(row.xpath('td')):
                if cell_no == 0:
                    try:
                        cities.append(cell.xpath('text()').extract_first().strip())
                    except AttributeError:
                        pass
                else:
                    states.append(cell.xpath('text()').extract_first().strip())
        total -= 1
        if total == 0:
            cities = [c for c in cities if c != '&nbsp']
            states = [s for s in states if s != '&nbsp']

            all_data.append(data)        
            all_cities.append(cities)
            all_states.append(states)
        i += 1                

        
    ##################################
    ## format and clean 
    
    # format cities
    all_cities = [['{} - {}'.format(city, state) for city, state in zip(cities, states)] for cities, states in zip(all_cities, all_states)]
    all_cities = [[c.upper() for c in cities] for cities in all_cities]

    # create dataframe
    columns.remove('Cidade')
    columns.remove('UF')
    df = pd.DataFrame(all_data, columns=columns)
    
    # remove unused columns
    good_columns = [c for c in df.columns if not c.startswith('Jogo')]
    df = df[good_columns]
    
    # rename columns
    df.columns = ['roundno', 'date', 'winners14', 'shared14', 'accumulated', 'accumulated14', 
        'winners13', 'shared13', 'winners12', 'shared12', 'total_revenue', 'prize_estimative']
    
    # make the types right        
    df['roundno'] = df.roundno.apply(_read_int)
    df['date'] = pd.to_datetime(df.date, dayfirst=True)
    df['winners14'] = df.winners14.apply(_read_int)
    df['winners13'] = df.winners13.apply(_read_int)
    df['winners12'] = df.winners12.apply(_read_int)
    df['shared14'] = df.shared14.apply(_read_float)
    df['shared13'] = df.shared13.apply(_read_float)
    df['shared12'] = df.shared12.apply(_read_float)
    df['accumulated'] = df.accumulated.apply(lambda x: x == 'SIM')
    df['accumulated14'] = df.accumulated14.apply(_read_float)
    df['total_revenue'] = df.total_revenue.apply(_read_float)
    df['prize_estimative'] = df.prize_estimative.apply(_read_float)
        
    # set index
    df = df.set_index('roundno')
    
    return df, all_cities

@click.command()
@click.argument('htm_location', type=click.Path(exists=True))
@click.argument('df_filename', type=click.Path(writable=True))
@click.argument('cities_filename', type=click.Path(writable=True))
def extract_files(htm_location, df_filename, cities_filename):
    # extract
    df, cities = extract_table(htm_location)
    
    # save
    with open(df_filename, mode='wb') as fp:
        pickle.dump(df, fp)
    with open(cities_filename, mode='wb') as fp:
        pickle.dump(cities, fp)
    
    return 0

if __name__ == '__main__':
    extract_files()
