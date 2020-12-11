import tree_sitter

def process(dirname):
	print("PROCESS")

if __name__ == "__main__":
	## Define static pathnames
	lib_path = 'build/my-languages.so'
	tree_sitter_python_path = 'tree-sitter-python'
	test_dir = 'test'

	## Initialize Python parser
	tree_sitter.Language.build_library(
	  lib_path,
	  [tree_sitter_python_path]
	)
	PY_LANGUAGE = tree_sitter.Language(lib_path, 'python')
	parser = tree_sitter.Parser()
	parser.set_language(PY_LANGUAGE)

	## Parse file
	with open('{dir}/foo.py'.format(dir=test_dir), 'r') as file:
		file_text = file.read()
	tree = parser.parse(bytes(file_text, 'utf8'))

	## Print file
	string = tree.root_node.sexp()
	print(string)