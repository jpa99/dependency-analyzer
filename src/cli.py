import sys
import utils
from analysis import *

## Help routine
def help():
	print("\nThe following arguments can be passed in the command line for this program:")
	print("   * [-h]: displays a list of arguments that can be included")
	print("   * [<dirpath>]: produces dependency graph for the Python directory <dirpath>\n\n")
	exit(0)

## Parse command line arguments
def parse_args(args):
	num_args = len(args)

	## Handle help flag
	help_flag = len(args) > 0 and args[0] == "-h"
	if help_flag:
		help()

	## Verify that arguments list is nonempty
	args_invalid = num_args < 2
	if args_invalid:
		print("\n[Command Line Error]: Missing arguments.", file=sys.stderr)
		help()

	## Ensure directory and file are valid 
	arg1 = args[0]
	arg2 = args[1]
	if not utils.is_valid_dir(arg1):
		print("\n[Command Line Error] Invalid directory \"{dirpath}\".".format(dirpath=arg1), file=sys.stderr)
		help()
	
	elif not utils.is_valid_file(arg2):
		print("\n[Command Line Error] Invalid file \"{filepath}\".".format(filepath=arg2), file=sys.stderr)
		help()
	else:
		dependency_analyzer = DependencyAnalyzer()
		dependency_analyzer.run(arg1, arg2)

	## Ignore trailing arguments 


