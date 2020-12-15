import utils
from parser import Parser

class DependencyAnalyzer():
	def __init__(self):
		self.parser = Parser()
		self.packages = utils.get_packages()
		self.graph = {}

	def is_stdlib(self, import_name):
		lib_name = "{import_name}.py".format(import_name=import_name)
		return lib_name in self.packages

	def is_site_package(self, import_name):
		package_name = "site_packages.{import_name}.py".format(import_name=import_name)
		return package_name in self.packages

	def is_package(self, import_name):
		return self.is_stdlib(import_name) or self.is_site_package(import_name)

	def print_ast(self, node, count):
		tab = " "*4*count
		print(tab + node.type)
		for child in node.children:
			print_ast(child, count+1)

	def extract_string(self, start_point, end_point, lines):
		startline, startidx = start_point
		endline, endidx = end_point
		if startline == endline:
			return lines[startline][startidx:endidx]

		currline = startline + 1
		substring_list = [lines[startline][startidx:]]
		while currline < endline:
			substring_list.append(lines[currline])
		substring_list.append(lines[endline][:endidx])
		return "".join(substring_list)

	## Assumption: no multi-line identifiers
	def extract_dotted_name(self, dotted_name_node, lines):
		children = dotted_name_node.children
		identifier_list = []
		for i in range(0, dotted_name_node.child_count, 2):
			assert children[i].start_point[0] == children[i].end_point[0]
			identifier = self.extract_string(children[i].start_point, children[i].end_point, lines)
			identifier_list.append(identifier)
		return ".".join(identifier_list)

	def handle_dotted_name(self, filepath, dotted_name_node, lines):
		dotted_name = self.extract_dotted_name(dotted_name_node, lines)
		
		parentdir = utils.extract_parent_directory(filepath)
		import_file = dotted_name.replace(".", "/")
		import_path = "{parentdir}/{import_file}.py".format(parentdir = parentdir, import_file = import_file)

		if utils.is_valid_python_file(import_path):
			self.graph[filepath].add(import_path)
			self.process_file(import_path)
		elif self.is_package(dotted_name):
			self.graph[dotted_name] = set()
			label = "(stdlib)" if self.is_stdlib(dotted_name) else "(site_package)"
			labeled_name = "{dotted_name} {label}".format(dotted_name=dotted_name, label=label)
			self.graph[filepath].add(labeled_name)
		else:
			print("INVALID IMPORT {}".format(import_path))
		
	
	def handle_aliased_import(self, filepath, aliased_import_node, lines):
		dotted_name_node, as_node, alias_node = aliased_import_node.children
		self.handle_dotted_name(filepath, dotted_name_node, lines)
		## TODO: handle alias

	def handle_import(self, filepath, import_stmt, lines):
		for child in import_stmt.children:
			if child.type == "import":
				pass
			elif child.type == "dotted_name":
				self.handle_dotted_name(filepath, child, lines)
			elif child.type == "aliased_import":
				self.handle_aliased_import(filepath, child, lines)
			elif child.type == ",":
				pass
			else:
				assert False

	## Generate dependency graph
	def process_file(self, filepath):
		# Ensure that we don't repeat
		if filepath in self.graph:
			return

		self.graph[filepath] = set()
		tree, lines = self.parser.parse_file(filepath)
		import_statements = [node for node in tree.root_node.children if node.type == 'import_statement']
		import_from_statements = [node for node in tree.root_node.children if node.type == 'import_from_statement']
	
		for import_stmt in import_statements:
			self.handle_import(filepath, import_stmt, lines)

	def process(self, dirpath, target_filepath):
		## clear graph
		self.graph = {}
		
		## Parse directory contents
		if not utils.directory_contains_file(dirpath, target_filepath):
			print("INPUT ERROR: File not within directory")
			return

		self.process_file(target_filepath)

		return self.graph

	def dependency_paths(self, node):
		dependencies = []
		if node not in self.graph:
			return dependencies

		def visit(u):
			for dependency in self.graph[node]:
				pass

	def run(self, dirpath, target_filepath):
		print(self.process(dirpath, target_filepath))

