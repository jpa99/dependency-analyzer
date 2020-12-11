import sys
import os
from analysis import process


## Help routine
def help():
	print("\nThe following arguments can be passed in the command line for this program:\n")
	print("   * [-h]: displays a list of arguments that can be included\n")
	print("   * [<dirname>]: produces dependency graph for the Python directory <dirname>\n\n")


## Checks if directory name is valid
def isValidDir(dirname):
	return True


### COMMAND LINE PARSER
if __name__ == "__main__":

	args = sys.argv[1:]
	num_args = len(args)

	## Verify that arguments list is nonempty
	if num_args < 1:
		print("\n[Command Line Error]: Missing arguments.", file=sys.stderr)
		help()
		exit(0)

	## Handle first input argument 
	input_arg = args[0]
	if input_arg == "-h": # Case: help flag
		help()
	elif isValidDir(input_arg): # Case: produce graph
		process(input_arg)

	## Handle unrecognized argument
	else:
		print("\n[Command Line Error] Invalid directory name \"{dirname}\".".format(dirname=input_arg), file=sys.stderr)
		help()