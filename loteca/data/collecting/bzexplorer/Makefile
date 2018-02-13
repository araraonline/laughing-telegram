db.sqlite3: db.py
	python db.py create_db db.sqlite3

createtable_leagues: db.py db.sqlite3
	python db.py create_leagues_table db.sqlite3

collect_leagues: scrap_leagues.py db.py createtable_leagues
	python scrap_leagues.py world db.sqlite3
	python scrap_leagues.py south-america db.sqlite3
	python scrap_leagues.py europe db.sqlite3
	python scrap_leagues.py brazil db.sqlite3

clean:
	rm db.sqlite3


.PHONY: createtable_leagues collect_leagues clean
