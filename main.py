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

tree = parser.parse(bytes("""
import math
from bar import *

def foo():
    if test == math.pow(2, 3):
        baz()
""", "utf8"))

string = tree.root_node.sexp()
print(string)
