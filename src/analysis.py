import utils
import sys
from parser import Parser

## Node represents a file or package that is imported
class Node():
    def __init__(self, name, ID, label="", alias=""):
        self.name = name    # name used by the importing file 
        self.ID = ID        # filepath or package name which uniquely identifies the file
        self.label = label  # metadata about the node (e.g. 'stdlib' or 'unused') 
        self.alias = alias  # alias used by importing file

    def __str__(self):
        label_string = " ({label})".format(label=self.label) if self.label else ""
        return "{name}{label_string}".format(name=self.name, label_string=label_string)

## File contains information about a particular file
class File():
    def __init__(self, filepath, lines):
        self.filepath = filepath
        self.lines = lines

## DependencyAnalyzer class to analyze dependencies for given file and directory 
class DependencyAnalyzer():
    def __init__(self):
        self.parser = Parser()                # tree-sitter Python parser
        self.packages = utils.get_packages()  # list of all available packages
        self.graph = {}                       # dependency graph adjacency set
        self.import_delegate = {              # delegates each identifier to a handler
            "dotted_name": self.handle_dotted_name,
            "aliased_import": self.handle_aliased_import,
            "wildcard_import": self.handle_wildcard_import,
        }
        for value in ["import", ",", "(", ")"]:
            self.import_delegate[value] = lambda x,y,z: None

    ## Update package list to add newly installed packages
    def refresh_packages(self):
        self.packages = utils.get_packages()

    ## Clear the graph and refresh packages
    def reset(self):
        self.refresh_packages()
        self.graph = {}

    ## Check if an import is a stdlib module
    def is_stdlib(self, import_name):
        lib_name = "{import_name}.py".format(import_name=import_name)
        return lib_name in self.packages

    ## Check if an import is a site package
    def is_site_package(self, import_name):
        package_name = "site_packages.{import_name}.py".format(import_name=import_name)
        return package_name in self.packages

    ## Check if an import is an internal/external library 
    def is_library(self, import_name):
        return self.is_stdlib(import_name) or self.is_site_package(import_name)

    ## Check if a tree-sitter node is an import statement
    def is_import(self, node):
        return node.type == "import_statement" or node.type == "import_from_statement"

    ## Display the AST via DFS
    def print_ast(self, node, count):
        tab = " "*4*count
        print(tab + node.type)
        for child in node.children:
            print_ast(child, count+1)

    ## Extract string from file given certain node start and end points
    def extract_string(self, node, lines):
        startline, startidx = node.start_point
        endline, endidx = node.end_point
        if startline == endline:
            return lines[startline][startidx:endidx]

        currline = startline + 1
        substring_list = [lines[startline][startidx:]]
        while currline < endline:
            substring_list.append(lines[currline])
        substring_list.append(lines[endline][:endidx])
        return "".join(substring_list)

    ## Extracts the string corresponding to a dotted name node
    def extract_dotted_name(self, dotted_name_node, lines):
        children = dotted_name_node.children
        identifier_list = []
        for child in children:
            if child.type == ".":
                identifier_list.append(".")
            else:
                assert child.start_point[0] == child.end_point[0] ## Assumption: no multi-line identifiers
                identifier = self.extract_string(child, lines)
                identifier_list.append(identifier)
        return "".join(identifier_list)

    ## Resolves each import given some optional context representing a parent absolute or relative module 
    ## for a statement "from X import Y as Z", we have either
    ##
    ##      (1) Y is a module within local module X 
    ##      (2) Y is an attribute within local module X
    ##      (3) Y is a module within external module X
    ##      (4) Y is an attribute within external module X

    def handle_dotted_name(self, file, node, context_node, alias=""):
        dotted_name = self.extract_dotted_name(node, file.lines)
        if not alias:
            alias = dotted_name

        import_file = utils.get_path(dotted_name)
        context_dotted_name = dotted_name
        parent_dir = utils.extract_parent_directory(file.filepath)
        context_path = parent_dir
        
        context = self.extract_dotted_name(context_node, file.lines) if context_node else ""
        if context:
            context_path = "{parent_dir}/{context}".format(parent_dir = parent_dir, context=utils.get_path(context))
            context_dotted_name = "{context}.{dotted_name}".format(context=context, dotted_name=dotted_name)

        context_module_path = "{context_path}.py".format(context_path = context_path)
        package_path = "{context_path}/{import_file}".format(context_path=context_path, import_file = import_file)
        module_path = "{package_path}.py".format(package_path = package_path)

        # Check if import is a submodule of a local module
        if utils.is_valid_module(module_path):
            node = Node(name=context_dotted_name, ID=module_path, alias=alias)
            self.graph[file.filepath].add(node)
            self.process_file(module_path)

        # Check if import is an attribute of a local module
        elif utils.is_valid_module(context_module_path):
            node = Node(name=context, ID=context_module_path, alias=alias)
            self.graph[file.filepath].add(node)
            self.process_file(context_module_path)

        # Check if import is a local package
        elif utils.is_valid_package(package_path):
            self.process_dir(file.filepath, context_dotted_name, package_path)

        # Check if import is a library module
        elif self.is_library(context_dotted_name):
            label = "stdlib" if self.is_stdlib(context_dotted_name) else "site_package"
            node = Node(name=context_dotted_name, ID=context_dotted_name, label=label, alias=alias)
            self.graph[context_dotted_name] = set()
            self.graph[file.filepath].add(node)

        # Check if import is an attribute of a library
        elif self.is_library(context):
            label = "stdlib" if self.is_stdlib(context) else "site_package"
            node = Node(name=context, ID=context, label=label, alias=alias)
            self.graph[context] = set()
            self.graph[file.filepath].add(node)
        else:
            print("ERROR: Invalid import {context_dotted_name} in file {filepath}".format(context_dotted_name=context_dotted_name, filepath=file.filepath))
        
    ## Extract alias and handle import normally
    def handle_aliased_import(self, file, node, context):
        assert node.child_count == 3
        dotted_name_node, as_node, alias_node = node.children
        alias = self.extract_string(alias_node, file.lines)
        self.handle_dotted_name(file, dotted_name_node, context, alias=alias)

    ## Treat a wildcard import like a normal import 
    def handle_wildcard_import(self, file, node, context):
        self.handle_dotted_name(file, context, None, alias="")

    ## Handle each kind of import differently 
    def delegate_import(self, file, import_children, context):
        for node in import_children:
            if node.type in self.import_delegate:
                self.import_delegate[node.type](file, node, context)
            else:
                assert False

    ## Handle an import statement by differentiating between normal imports and imports 'from'
    def handle_import(self, file, node):
        ## If node is an import statement
        context = None
        import_children = node.children

        # If node is an import from statement, define context and adjust children
        if node.type == "import_from_statement":
            context = import_children[1]
            import_children = node.children[2:]

        self.delegate_import(file, import_children, context)

    ## Recursively process all files and subdirectories within given directory
    def process_dir(self, src_filepath, context_dotted_name, dirpath):
        for entry in utils.get_directory_contents(dirpath):
            entrypath = "{dirpath}/{entryname}".format(dirpath=dirpath, entryname=entry.name)
            if entry.is_dir() and utils.is_valid_package(entrypath):
                self.process_dir(src_filepath, context_dotted_name, entrypath)
            elif utils.is_valid_module(entrypath):
                module_name = "{context_dotted_name}.{entryname}".format(context_dotted_name=context_dotted_name, entryname=entry.name)
                node = Node(name=module_name, ID=entrypath)
                self.graph[src_filepath].add(node)
                self.process_file(entrypath)

    ## DFS on a given file to extract dependencies
    def process_file(self, filepath):
       # Ensure that we don't revisit files
        if filepath in self.graph:
            return

        print("[DependencyAnalyzer::process_file] Processing File {file}".format(file=filepath))
        # Iterate through the AST and process any imports
        imports = []
        self.graph[filepath] = set()
        tree, lines = self.parser.parse_file(filepath)
        file = File(filepath, lines)
        
        for node in tree.root_node.children:
            if self.is_import(node):
                self.handle_import(file, node)

    ## Generates dependency graph for given directory and filepath 
    def process(self, dirpath, filepath):
        self.reset() # Clear dependency graph 
        
        # Parse directory contents
        if not utils.directory_contains_file(dirpath, filepath):
            print("Error: ")
            return

        self.process_file(filepath)

    ## DFS through dependency graph to generate all paths
    def dependency_paths(self, filepath):
        # Ensure that filepath is valid
        dependencies = []
        if filepath not in self.graph:
            return dependencies

        # Initialize root node as filepath
        name = utils.extract_filename(filepath)
        root = Node(name=name, ID=filepath)
        context = [root]
        visited = set()

        ## DFS through graph and add path to dependencies list each time we encounter a leaf
        def visit(u):
            if self.graph[u.ID] and u.ID not in visited:
                visited.add(u.ID)
                for v in self.graph[u.ID]:
                    context.append(v)
                    visit(v)
                    context.pop()
            else:
                dependencies.append(list(context))
            
        visit(root)
        return dependencies

    ## Generate all dependency paths and pretty print them
    def print_dependency_paths(self, filepath):
        dependency_paths = self.dependency_paths(filepath)
        for path in dependency_paths:
            print("    "+" <- ".join(map(str, path[::-1])))

    ## Print dependency graph
    def print_graph(self):
        for node in self.graph:
            print(node)
            for adj in self.graph[node]:
                print("    "+str(adj))

    ## Produce and display dependency graph for a given file
    def run(self, dirpath, filepath):
        self.process(dirpath, filepath)
        self.print_graph()
        self.print_dependency_paths(filepath)

