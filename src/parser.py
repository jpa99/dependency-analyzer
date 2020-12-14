import tree_sitter

## Parser class to interface with tree-sitter
class Parser():
	## Initialize tree_sitter Python parser
	def __init__(self, lib_path = 'build/my-languages.so', tree_sitter_python_path = 'tree-sitter-python'):
		tree_sitter.Language.build_library(
		  lib_path,
		  [tree_sitter_python_path]
		)
		PY_LANGUAGE = tree_sitter.Language(lib_path, 'python')
		self.parser = tree_sitter.Parser()
		self.parser.set_language(PY_LANGUAGE)

	## Returns an abstract syntax tree for the specified file
	def parse_file(self, file):
		with open(file, 'r') as fd:
			contents = fd.read()
			return self.parser.parse(bytes(contents, 'utf8')), contents.splitlines(True)