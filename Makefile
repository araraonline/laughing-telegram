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
	find -type d -name __pycache__ -prune -exec rm -r {} \;



# Loteca file

### Download and extract loteca file
data/raw/d_loteca.zip:
	@echo Download loteca file
	@wget -nv -N --no-if-modified-since -P "data/raw/" "http://www1.caixa.gov.br/loterias/_arquivos/loterias/d_loteca.zip"

data/raw/loteca.htm: data/raw/d_loteca.zip
	@echo Extract loteca file
	@unzip -DD -d data/raw/ data/raw/d_loteca.zip
	@rm data/raw/LOTECA.GIF
	@mv data/raw/D_LOTECA.HTM data/raw/loteca.htm

### Preprocess loteca file
data/pre/lotecaf_rounds.pkl: loteca/data/pre/loteca_file.py \
				data/raw/loteca.htm
	@echo Preprocess loteca file
	@python -m loteca.data.pre.loteca_file $(word 2,$^) $@

### Process loteca file rounds
data/process/lotecaf_rounds.pkl: loteca/data/process/lotecaf_rounds.py \
					data/pre/lotecaf_rounds.pkl
	@echo Process loteca file rounds
	@python -m loteca.data.process.lotecaf_rounds $(word 2,$^) $@



# Loteca site

### Collect data from loteca site
data/raw/loteca_site.pkl: loteca/data/raw/loteca_site.py
	@echo Collect data from loteca site
	@python -m loteca.data.raw.loteca_site $@

### Preprocess loteca site
data/pre/lotecas_matches.pkl: loteca/data/pre/loteca_site.py \
				data/raw/loteca_site.pkl
	@echo Preprocess loteca site
	@python -m loteca.data.pre.loteca_site $(word 2,$^) $@



# BetExplorer

### Collect BetExplorer matches
data/raw/betexplorer.sqlite3:
	@echo Collect BetExplorer matches
	@cd loteca/data/raw/betexplorer/ && $(MAKE) collect-matches
	@cp loteca/data/raw/betexplorer/db.sqlite3 data/raw/betexplorer.sqlite3



# Loteca to BetExplorer

### Download list of countries (for team merging)
data/external/countries_pt.json data/external/countries_en.json:
	@echo Download list of countries
	@wget -nv -O "data/external/countries_pt_BR.json" "https://raw.githubusercontent.com/umpirsky/country-list/master/data/pt_BR/country.json"
	@wget -nv -O "data/external/countries_en.json" "https://raw.githubusercontent.com/umpirsky/country-list/master/data/en/country.json"

### Generate Loteca to BetExplorer teams dictionary
data/interim/teams_ltb.pkl: loteca/data/interim/teams/loteca_to_betexp.py \
				data/raw/betexplorer.sqlite3 \
				data/pre/lotecas_matches.pkl \
				data/external/countries_en.json \
				data/external/countries_pt_BR.json
	@echo Generate Loteca to BetExplorer teams dictionary
	@python -m loteca.data.interim.teams.loteca_to_betexp $(word 2,$^) $(word 3,$^) $(word 4,$^) $(word 5,$^) $@

loteca/data/interim/teams/betexplorer.py: \
	loteca/data/interim/teams/commons.py \
	loteca/data/interim/teams/util.py
loteca/data/interim/teams/loteca.py: \
	loteca/data/interim/teams/commons.py \
	loteca/data/interim/teams/util.py
loteca/data/interim/teams/loteca_to_betexp.py: \
	loteca/data/interim/teams/betexplorer.py \
	loteca/data/interim/teams/country.py \
	loteca/data/interim/teams/loteca.py \
	loteca/data/interim/teams/util.py



# Updates

.PHONY: update-loteca-file
update-loteca-file: FORCE
	@echo Download and extract loteca file
	@wget -nv -N --no-if-modified-since -P "data/raw/" "http://www1.caixa.gov.br/loterias/_arquivos/loterias/d_loteca.zip"
	@unzip -DD -d data/raw/ data/raw/d_loteca.zip
	@rm data/raw/LOTECA.GIF
	@mv data/raw/D_LOTECA.HTM data/raw/loteca.htm

.PHONY: update-loteca-site
update-loteca-site: FORCE
	@echo Collect data from loteca site
	@python -m loteca.data.raw.loteca_site data/raw/loteca_site.pkl

.PHONY: update-betexplorer
update-betexplorer: FORCE
	@echo Collect BetExplorer matches
	@cd loteca/data/raw/betexplorer/ && $(MAKE) collect-matches
	@cp loteca/data/raw/betexplorer/db.sqlite3 data/raw/betexplorer.sqlite3

.PHONY: update-countries-dict
update-countries-dict: FORCE
	@echo Download list of countries
	@wget -nv -O "data/external/countries_pt_BR.json" "https://raw.githubusercontent.com/umpirsky/country-list/master/data/pt_BR/country.json"
	@wget -nv -O "data/external/countries_en.json" "https://raw.githubusercontent.com/umpirsky/country-list/master/data/en/country.json"



# Misc

.PHONY: reports
reports: FORCE
	@echo Generate reports
	@mkdir -p reports
	@cd notebooks && find -name '*.ipynb' ! -name '*-checkpoint.ipynb' -exec jupyter nbconvert {} --to html --output-dir html/ \;

.PHONY: FORCE
FORCE:
