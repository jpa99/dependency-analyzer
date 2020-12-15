install:
	pip3.6 install -r requirements.txt

test:
	./analyze test test/foo.py

.PHONY: install test