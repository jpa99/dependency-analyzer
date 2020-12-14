from parser import Parser
import distutils.sysconfig as sysconfig
import os

## Returns a list of file paths within the specified directory
def get_directory_files(dirpath):
	files = []
	for entry in os.scandir(dirpath):
		if entry.is_file():
			files.append(entry.path)
		else:
			files += parse_files(entry.path)
	return files

def get_stdlib():
	lib = set()
	std_lib = sysconfig.get_python_lib(standard_lib=True)
	for top, dirs, files in os.walk(std_lib):
	    for name in files:
	        if name != '__init__.py' and name[-3:] == '.py':
	        	lib.add(name)
	return lib

def process(dirpath, target_filepath):
	## initialize
	parser = Parser()
	stdlib = get_stdlib()
	
	## Parse directory contents
	directory_files = get_directory_files(dirpath)
	if filepath not in directory_files:
		return None

	## Generate dependency graph
	graph = {}
	def generate_dependency_graph(filepath, import_statement):
		if filepath in graph:
			return

		graph[filepath] = set()
		tree, lines = parser.parse_file(filepath)
		import_statements = [node for node in tree.root_node.children if node.type == 'import_statement']
		import_from_statements = [node for node in tree.root_node.children if node.type == 'import_from_statement']
	
		for import_stmt in import_statements:
			pass




	generate_dependency_graph(target_filepath)

	## TODO: pretty print graph
	print(graph)

