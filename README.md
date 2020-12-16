# dependency-analyzer

Simple CLI tool to analyze dependencies for a given Python directory and file. You must have Python 3.6 installed along with pip 3.6. To run, clone this repo and run the Makefile via `make install` to install the relevant libraries. Then, running the bash script `./analyze <dirpath> <filepath>` with the specified valid directory `<dirpath>` and file `<filepath>` will print a sequence of dependency chains for the specified file. 

Alternatively, the `src/analyzer.py` file contains a Python class called `DependencyAnalyzer` which can be instantiated, and the same output can be achieved by calling the `run(<dirpath>, <filepath>)` method on a `DependencyAnalyzer` instance.
