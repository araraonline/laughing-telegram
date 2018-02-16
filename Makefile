dummy:
	# this will do nothing

clean:
	rm -f data/raw/*
	rm -f data/interim/*
	rm -f data/processed/*


# Download loteca file
data/raw/d_loteca.zip: FORCE
	@echo Downloading loteca file...
	@wget -nv -N --no-if-modified-since -P "data/raw/" "http://www1.caixa.gov.br/loterias/_arquivos/loterias/d_loteca.zip"
	@echo Done!
	@echo

# Unzip loteca file
data/raw/loteca_file.htm: data/raw/d_loteca.zip
	@echo Unzipping loteca file...
	@unzip -DD -d data/raw/ data/raw/d_loteca.zip
	@rm data/raw/LOTECA.GIF
	@mv data/raw/D_LOTECA.HTM data/raw/loteca_file.htm
	@echo

# Extract loteca file
data/interim/loteca_file_rounds.pkl data/interim/loteca_file_cities.pkl: loteca/data/processing/extract_loteca_file.py data/raw/loteca_file.htm
	@echo Extracting data from loteca file...
	@python $< $(word 2,$^) data/interim/loteca_file_rounds.pkl data/interim/loteca_file_cities.pkl

# Collect data from loteca site
data/raw/loteca_site.pkl: loteca/data/collecting/collect_loteca_site.py data/interim/loteca_file_rounds.pkl
	@echo Collecting data from loteca site...
	@python $< $(word 2,$^) $@
	@echo

# Process data from loteca site
data/interim/loteca_site_rounds.pkl data/interim/loteca_site_games.pkl data/interim/loteca_site_cities.pkl: loteca/data/processing/extract_loteca_site.py data/raw/loteca_site.pkl
	@echo Processing data from loteca site...
	@python $< $(word 2,$^) data/interim/loteca_site_rounds.pkl data/interim/loteca_site_games.pkl data/interim/loteca_site_cities.pkl

# Merge rounds from loteca site and file 
data/interim/loteca_rounds.pkl: loteca/data/merging/merge_loteca_rounds.py data/interim/loteca_file_rounds.pkl data/interim/loteca_site_rounds.pkl
	@echo Merging rounds from loteca site and file...
	@python $< $(word 2,$^) $(word 3,$^) $@

# Calculate prizes for loteca rounds
data/processed/loteca_rounds.pkl: loteca/data/processing/process_loteca_rounds.py data/interim/loteca_rounds.pkl
	@echo Calculating prizes for loteca rounds...
	@python $< $(word 2,$^) $@

# Collect BetExplorer matches
data/raw/betexplorer.sqlite3: FORCE
	@echo Collecting BetExplorer matches...
	@cd loteca/data/collecting/betexplorer/ && $(MAKE) collect_matches
	@cp loteca/data/collecting/betexplorer/db.sqlite3 data/raw/betexplorer.sqlite3
	@echo Done!
	@echo

# Download list of countries (for team merging)
data/external/countries_pt.json data/external/countries_en.json:
	@echo Downloading list of countries...
	@wget -nv -O "data/external/countries_pt.json" "https://raw.githubusercontent.com/umpirsky/country-list/master/data/pt_BR/country.json"
	@wget -nv -O "data/external/countries_en.json" "https://raw.githubusercontent.com/umpirsky/country-list/master/data/en/country.json"
	@echo Done!
	@echo


.PHONY: all clean FORCE
FORCE:
