leagues_start_year = 2010

collect_leagues: scrap_leagues.py 
	python scrap_leagues.py world --start-year $(leagues_start_year)
	python scrap_leagues.py south-america --start-year $(leagues_start_year)
	python scrap_leagues.py brazil --start-year $(leagues_start_year)
	python scrap_leagues.py europe --start-year $(leagues_start_year)

clean:
	rm db.sqlite3


.PHONY: collect_leagues clean
