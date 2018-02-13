leagues_start_year = 2010

collect_leagues: collect_leagues.py 
	python collect_leagues.py world --start-year $(leagues_start_year)
	python collect_leagues.py south-america --start-year $(leagues_start_year)
	python collect_leagues.py brazil --start-year $(leagues_start_year)
	python collect_leagues.py europe --start-year $(leagues_start_year)

clean:
	rm db.sqlite3


.PHONY: collect_leagues clean
