# Main {{{1

main_db = 'data/db.sqlite3'

dummy:
	# this will do nothing

.PHONY: clean
clean:
	rm -f data/external/*
	rm -f data/interim/*
	rm -f data/pre/*
	rm -f data/process/*
	rm -f data/raw/*

.PHONY: clean-cache
clean-cache:
	find -type f -name '*.pyc' -exec rm -r {} \;
	find -type d -name '__pycache__' -prune -exec rm -r {} \;


# Loteca file (rounds) {{{1

### Download and extract file
data/raw/d_loteca.zip:
	@echo Download loteca file
	@wget -nv -N --no-if-modified-since -P "data/raw/" "http://www1.caixa.gov.br/loterias/_arquivos/loterias/d_loteca.zip"

data/raw/loteca.htm: data/raw/d_loteca.zip
	@echo Extract loteca file
	@unzip -DD -d data/raw/ data/raw/d_loteca.zip
	@rm data/raw/LOTECA.GIF
	@mv data/raw/D_LOTECA.HTM data/raw/loteca.htm

### Extract rounds from file
data/pre/loteca_rounds.pkl: src/data/pre/loteca_rounds.py \
							 data/raw/loteca.htm
	@echo Extract loteca rounds from file
	@python -m src.data.pre.loteca_rounds $(word 2,$^) $@

### Process loteca rounds
data/process/loteca_rounds.pkl: src/data/process/loteca_rounds.py \
								 data/pre/loteca_rounds.pkl
	@echo Process loteca rounds
	@python -m src.data.process.loteca_rounds $(word 2,$^) $@


# Loteca site (matches) {{{1

### Collect data from loteca site
data/raw/loteca_site.pkl: src/data/raw/loteca_site.py
	@echo Collect data from loteca site
	@python -m src.data.raw.loteca_site $@

### Extract matches from data
data/pre/loteca_matches.pkl: src/data/pre/loteca_matches.py \
							  data/raw/loteca_site.pkl
	@echo Extract matches from the loteca site data
	@python -m src.data.pre.loteca_matches $(word 2,$^) $@

### Process loteca matches
data/process/loteca_matches.pkl: src/data/process/loteca_matches.py \
								  data/pre/loteca_matches.pkl
	@echo Process loteca matches
	@python -m src.data.process.loteca_matches $(word 2,$^) $@


# BetExplorer {{{1

betexp_db = $(main_db)
leagues_start = '2009'  # the matches we are interested in start in 2009

### Collect BetExplorer leagues
data/flags/betexp_leagues: src/data/raw/betexplorer/collect_leagues.py
	@echo Collect BetExplorer leagues
	@python -m src.data.raw.betexplorer.collect_leagues world          $(leagues_start) $(betexp_db)
	@python -m src.data.raw.betexplorer.collect_leagues south-america  $(leagues_start) $(betexp_db)
	@python -m src.data.raw.betexplorer.collect_leagues brazil         $(leagues_start) $(betexp_db)
	@python -m src.data.raw.betexplorer.collect_leagues europe         $(leagues_start) $(betexp_db)
	@python -m src.data.raw.betexplorer.collect_leagues italy          $(leagues_start) $(betexp_db)
	@python -m src.data.raw.betexplorer.collect_leagues france         $(leagues_start) $(betexp_db)
	@python -m src.data.raw.betexplorer.collect_leagues spain          $(leagues_start) $(betexp_db)
	@python -m src.data.raw.betexplorer.collect_leagues germany        $(leagues_start) $(betexp_db)
	@python -m src.data.raw.betexplorer.collect_leagues england        $(leagues_start) $(betexp_db)
	@touch $@

### Collect BetExplorer matches
data/flags/betexp_matches: src/data/raw/betexplorer/collect_matches.py \
							data/flags/betexp_leagues
	@echo Collect BetExplorer matches
	@python -m src.data.raw.betexplorer.collect_matches $(betexp_db)
	@touch $@

### Collect BetExplorer odds
data/flags/betexp_odds: src/data/raw/betexplorer/collect_odds.py \
						 data/flags/betexp_matches \
						 data/interim/betexp_matchlist.pkl
	@echo Collect BetExplorer odds
	@python -m src.data.raw.betexplorer.collect_odds $(word 3,$^) $(betexp_db)
	@touch $@


# Loteca to BetExplorer {{{1

### Download external list of countries (for team merging)
data/external/countries_pt.json data/external/countries_en.json:
	@echo Download external list of countries
	@wget -nv -O "data/external/countries_pt_BR.json" "https://raw.githubusercontent.com/umpirsky/country-list/master/data/pt_BR/country.json"
	@wget -nv -O "data/external/countries_en.json" "https://raw.githubusercontent.com/umpirsky/country-list/master/data/en/country.json"

### Link country lists
data/interim/countries.pkl: src/misc/json_to_pickle.py \
							src/misc/link_dictionaries.py \
							 data/external/countries_en.json \
							 data/external/countries_pt_BR.json
	@echo Link country lists
	@python -m src.misc.json_to_pickle $(word 3,$^) data/interim/countries_en.pkl
	@python -m src.misc.json_to_pickle $(word 4,$^) data/interim/countries_pt_BR.pkl
	@python -m src.misc.link_dictionaries data/interim/countries_pt_BR.pkl data/interim/countries_en.pkl $@
	@rm data/interim/countries_en.pkl
	@rm data/interim/countries_pt_BR.pkl

### Generate Loteca to BetExplorer teams dictionary
data/interim/ltb_teams.pkl: src/data/interim/ltb_teams.py \
							 data/flags/betexp_matches \
							 data/process/loteca_matches.pkl \
							 data/interim/countries.pkl
	@echo Generate Loteca to BetExplorer teams dictionary
	@python -m src.data.interim.ltb_teams $(betexp_db) $(word 3,$^) $(word 4,$^) $@

### Generate Loteca to BetExplorer matches dictionary:
data/interim/ltb_matches.pkl: src/data/interim/ltb_matches.py \
							   data/process/loteca_matches.pkl \
							   data/flags/betexp_matches \
							   data/interim/ltb_teams.pkl
	@echo Generate Loteca to BetExplorer matches dictionary
	@python -m src.data.interim.ltb_matches $(word 2,$^) $(betexp_db) $(word 4,$^) $@

### Create list of matches found
data/interim/betexp_matchlist.pkl: src/misc/extract_dict_values.py \
									data/interim/ltb_matches.pkl
	@echo Create list of matches to be scraped
	@python -m src.misc.extract_dict_values $(word 2,$^) $@

data/interim/loteca_matchlist.pkl: src/misc/extract_dict_keys.py \
									data/interim/ltb_matches.pkl
	@echo Create list of matches found
	@python -m src.misc.extract_dict_keys $(word 2,$^) $@


# Updates {{{1

.PHONY: update-loteca-file
update-loteca-file: FORCE
	@echo Download loteca file
	@wget -nv -N --no-if-modified-since -P "data/raw/" "http://www1.caixa.gov.br/loterias/_arquivos/loterias/d_loteca.zip"
	@echo Extract loteca file
	@unzip -DD -d data/raw/ data/raw/d_loteca.zip
	@rm data/raw/LOTECA.GIF
	@mv data/raw/D_LOTECA.HTM data/raw/loteca.htm

.PHONY: update-loteca-site
update-loteca-site: FORCE
	@echo Collect data from loteca site
	@python -m src.data.raw.loteca_site data/raw/loteca_site.pkl


# Misc {{{1

.PHONY: reports
reports: FORCE
	@echo Generate reports
	@mkdir -p reports
	@cd notebooks && find -name '*.ipynb' ! -name '*-checkpoint.ipynb' -exec jupyter nbconvert {} --to html --output-dir html/ \;

.PHONY: FORCE
FORCE:
