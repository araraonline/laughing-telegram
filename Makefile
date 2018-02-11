dummy:

clean:
	rm -f data/raw/*
	rm -f data/interim/*
	rm -f data/processed/*


data/raw/d_loteca.zip: FORCE
	wget -N --no-if-modified-since -P "data/raw/" "http://www1.caixa.gov.br/loterias/_arquivos/loterias/d_loteca.zip"

data/raw/loteca_file.htm: data/raw/d_loteca.zip
	unzip -DD -d data/raw/ data/raw/d_loteca.zip
	rm data/raw/LOTECA.GIF
	mv data/raw/D_LOTECA.HTM data/raw/loteca_file.htm

data/interim/loteca_file_rounds.pkl data/interim/loteca_file_cities.pkl: loteca/data/processing/extract_loteca_file.py data/raw/loteca_file.htm
	python $< $(word 2,$^) data/interim/loteca_file_rounds.pkl data/interim/loteca_file_cities.pkl

data/raw/loteca_site.pkl: loteca/data/collecting/collect_loteca_site.py data/interim/loteca_file_rounds.pkl
	@echo $?
	python $< $(word 2,$^) $@

data/interim/loteca_site_rounds.pkl data/interim/loteca_site_games.pkl data/interim/loteca_site_cities.pkl: loteca/data/processing/extract_loteca_site.py data/raw/loteca_site.pkl
	python $< $(word 2,$^) data/interim/loteca_site_rounds.pkl data/interim/loteca_site_games.pkl data/interim/loteca_site_cities.pkl

data/interim/loteca_rounds.pkl: loteca/data/merging/merge_loteca_rounds.py data/interim/loteca_file_rounds.pkl data/interim/loteca_site_rounds.pkl
	python $< $(word 2,$^) $(word 3,$^) $@

data/processed/loteca_rounds.pkl: loteca/data/processing/process_loteca_rounds.py data/interim/loteca_rounds.pkl
	python $< $(word 2,$^) $@

.PHONY: all clean FORCE
FORCE:
