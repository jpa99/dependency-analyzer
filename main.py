import tree_sitter

tree_sitter.Language.build_library(
  # Store the library in the `build` directory
  'build/my-languages.so',

  # Include one or more languages
  ['tree-sitter-python']
)

PY_LANGUAGE = tree_sitter.Language('build/my-languages.so', 'python')

parser = tree_sitter.Parser()
parser.set_language(PY_LANGUAGE)

with open('test/foo.py', 'r') as file:
	file_text = file.read()
	
tree = parser.parse(bytes(file_text, 'utf8'))

string = tree.root_node.sexp()
print(string)
