leagues_start_year = 2009  # the matches we are interested in start in 2009


.PHONY: collect-leagues
collect-leagues: collect_leagues.py 
	python collect_leagues.py world --start-year $(leagues_start_year)
	python collect_leagues.py south-america --start-year $(leagues_start_year)
	python collect_leagues.py brazil --start-year $(leagues_start_year)
	python collect_leagues.py europe --start-year $(leagues_start_year)
	python collect_leagues.py italy --start-year $(leagues_start_year)
	python collect_leagues.py france --start-year $(leagues_start_year)
	python collect_leagues.py spain --start-year $(leagues_start_year)
	python collect_leagues.py germany --start-year $(leagues_start_year)
	python collect_leagues.py england --start-year $(leagues_start_year)

.PHONY: collect-matches
collect-matches: collect_matches.py collect-leagues
	python collect_matches.py

.PHONY: clean
clean:
	rm db.sqlite3
