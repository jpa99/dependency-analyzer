install:
	pip3.6 install -r requirements.txt

test:
	./analyze test test/foo.py -u -g

.PHONY: install test