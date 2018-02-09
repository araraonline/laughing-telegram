.phony: all clean
LOTECA_FILE_URL = "http://www1.caixa.gov.br/loterias/_arquivos/loterias/d_loteca.zip"


all:

clean:
	rm -f data/raw/*
	rm -f data/interim/*
	rm -f data/processed/*

data/raw/loteca.htm:
	wget $(LOTECA_FILE_URL) -O data/raw/d_loteca.zip
	unzip data/raw/d_loteca.zip -d data/raw
	rm data/raw/d_loteca.zip data/raw/LOTECA.GIF
	mv data/raw/D_LOTECA.HTM data/raw/loteca.htm

data/interim/loteca_df.pkl data/interim/loteca_cities.pkl: data/raw/loteca.htm
	python loteca/data/processing/extract_loteca.py data/raw/loteca.htm data/interim/loteca_df.pkl data/interim/loteca_cities.pkl
