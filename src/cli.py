import sys
import utils
import argparse
from analyzer import DependencyAnalyzer, Config


## Parse command line arguments
def parse_args():
	logging_levels = ["notset", "debug", "info", "warning", "error", "critical"]
	parser = argparse.ArgumentParser(description="Analyze dependencies for input Python file.")
	parser.add_argument("dirpath", type=str,
	                    help="directory path to analyze")
	parser.add_argument("filepath", type=str,
	                    help="python file path to analyze")

	parser.add_argument("-l", "--logging_level", type=str, default="error",
						choices=set(logging_levels),
	                    help="logging level")
	parser.add_argument("-s", "--search_imports", action='store_true',
	                    help="flag to search local machine and check if all dependencies are installed")
	parser.add_argument("-g", "--render_graph", action='store_true',
	                    help="flag to render dependency graph")
	parser.add_argument("-u", "--mark_unused", action='store_true',
	                    help="flag to mark unused dependencies")
	


	args = parser.parse_args()
	render_graph = args.render_graph

	if not utils.is_valid_dir(args.dirpath):
		print("\n[Command Line Error] Invalid directory \"{dirpath}\".".format(dirpath=args.dirpath), file=sys.stderr)

	
	elif not utils.is_valid_file(args.filepath):
		print("\n[Command Line Error] Invalid file \"{filepath}\".".format(filepath=args.filepath), file=sys.stderr)

	else:
		logging_level = logging_levels.index(args.logging_level)*10
		config = Config(logging_level=logging_level, resolve_all_imports=not args.search_imports, render_graph=args.render_graph, mark_unused = args.mark_unused)
		dependency_analyzer = DependencyAnalyzer(config)
		dependency_analyzer.run(args.dirpath, args.filepath)


