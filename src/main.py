import sys
import os
from analysis import process


## Help routine
def help():
	print("\nThe following arguments can be passed in the command line for this program:")
	print("   * [-h]: displays a list of arguments that can be included")
	print("   * [<dirpath>]: produces dependency graph for the Python directory <dirpath>\n\n")
	exit(0)


## Checks if directory name is valid
def isValidDir(dirpath):
	return os.path.isdir(dirpath)


### COMMAND LINE ARGUMENT PARSER
if __name__ == "__main__":

	args = sys.argv[1:]
	num_args = len(args)

	## Verify that arguments list is nonempty
	if num_args < 1:
		print("\n[Command Line Error]: Missing arguments.", file=sys.stderr)
		help()

	## Handle help argument 
	arg1 = args[0]
	arg2 = args[1]
	if arg1 == "-h": # Case: help flag
		help()
	
	## Ensure directory and file are valid 
	if not isValidDir(arg1):
		print("\n[Command Line Error] Invalid directory \"{dirpath}\".".format(dirpath=arg1), file=sys.stderr)
		help()
	elif not isValidFile(arg2):
		print("\n[Command Line Error] Invalid file \"{filepath}\".".format(filepath=arg2), file=sys.stderr)
		help()
	else:
		process(arg1, arg2)

	## Ignore trailing arguments 




