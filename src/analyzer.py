import utils
import logging
import sys
import graphviz
from tree_sitter import Node as TreeSitterNode
from parser import Parser

## Node represents a file or package that is imported
class Node():
    def __init__(self, name: str, ID: str, labels=[], alias=""):
        self.name = name        # name used by the importing file 
        self.ID = ID            # filepath or package name which uniquely identifies the file
        self.labels = labels    # metadata about the node (e.g. 'stdlib' or 'unused') 
        self.alias = alias      # alias used by importing file

    def __str__(self):
        name_string = self.name
        if len(self.name) >= 2 and self.name[0] == "." and self.name[:2] != "..":
            name_string = self.name[1:]
        label_string = " ({label})".format(label=", ".join(self.labels)) if self.labels else ""
        return "{name_string}{label_string}".format(name_string=name_string, label_string=label_string)

    def __hash__(self):
      return hash((self.name, self.ID, len(self.labels), self.alias))

    def add_label(self, label):
        print(self.name, self.ID, len(self.labels))
        self.labels.append(label)

## File contains information about a particular file
class File():
    def __init__(self, filepath: str, lines: list):
        self.filepath = filepath
        self.lines = lines

## Config contains configuration information for the dependency analyzer
class Config():
    def __init__(self):
        self.logging_level = logging.DEBUG
        self.resolve_all_imports = True
        self.render_graph = True
        self.find_unused = True

## DependencyAnalyzer class to analyze dependencies for given file and directory 
class DependencyAnalyzer():
    def __init__(self, config = Config()):
        self.parser = Parser()                  # tree-sitter Python parser
        self.libraries = utils.get_libraries()  # list of all available libraries
        self.graph = {}                         # dependency graph adjacency set
        self.config = config                    # whether we should process imports that cannot be found
        self.import_delegate = {                # delegates each identifier to a handler
            "dotted_name": self.handle_dotted_name,
            "aliased_import": self.handle_aliased_import,
            "wildcard_import": self.handle_wildcard_import,
        }
        for value in ["import", ",", "(", ")"]:
            self.import_delegate[value] = lambda x,y,z: None

        logging.basicConfig(level=config.logging_level)

    ## Update package list to add newly installed libraries
    def refresh_packages(self):
        self.libraries = utils.get_libraries()

    ## Clear the graph and refresh libraries
    def reset(self):
        self.refresh_packages()
        self.graph = {}

    ## Check if an import is a stdlib module
    def is_stdlib(self, import_name: str) -> bool:
        lib_name = "{import_name}.py".format(import_name=import_name)
        return lib_name in self.libraries

    ## Check if an import is a site package
    def is_site_package(self, import_name: str) -> bool:
        package_name = "site_packages.{import_name}.py".format(import_name=import_name)
        return package_name in self.libraries

    ## Check if an import is an internal/external library 
    def is_library(self, import_name: str) -> bool:
        return self.is_stdlib(import_name) or self.is_site_package(import_name)

    ## Check if a tree-sitter node is an import statement
    def is_import(self, tree_sitter_node: TreeSitterNode) -> bool:
        return tree_sitter_node.type == "import_statement" or tree_sitter_node.type == "import_from_statement"

    ## Display the parse tree via DFS
    def print_tree(self, tree_sitter_node: TreeSitterNode, count: int):
        tab = " "*4*count
        print(tab + tree_sitter_node.type)
        for child in tree_sitter_node.children:
            print_tree(child, count+1)

    ## Extract string from file given certain node start and end points
    def extract_string(self, tree_sitter_node: TreeSitterNode, lines: list) -> str:
        startline, startidx = tree_sitter_node.start_point
        endline, endidx = tree_sitter_node.end_point
        if startline == endline:
            return lines[startline][startidx:endidx]

        currline = startline + 1
        substring_list = [lines[startline][startidx:]]
        while currline < endline:
            substring_list.append(lines[currline])
        substring_list.append(lines[endline][:endidx])
        return "".join(substring_list)

    ## Extracts the string corresponding to a dotted name node
    def extract_dotted_name(self, dotted_name_node: TreeSitterNode, lines: list) -> str:
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
    ## Returns the identifier string bound to the import for the file unless the import is a wildcard import or package
    def handle_dotted_name(self, file: File, dotted_name_node: TreeSitterNode, context_node: TreeSitterNode, alias="") -> Node:
        dotted_name = self.extract_dotted_name(dotted_name_node, file.lines)
        if not alias:
            alias = dotted_name

        import_file = utils.get_path(dotted_name)
        context_dotted_name = dotted_name
        parent_dir = utils.extract_parent_directory(file.filepath)
        context_path = parent_dir
        
        # Process context iff this call corresponds to an import 'from' statement
        context = self.extract_dotted_name(context_node, file.lines) if context_node else ""
        context_dir = utils.get_path(context)
        context_init_path, context_module_path = "", ""
        if context_dir:
            context_path = "{parent_dir}/{context_dir}".format(parent_dir = parent_dir, context_dir=context_dir)
            context_dotted_name = "{context}.{dotted_name}".format(context=context, dotted_name=dotted_name)
            context_init_path = "{context_path}/__init__.py".format(context_path = context_path)
            context_module_path = "{context_path}.py".format(context_path = context_path)
        
        # Generate possible paths to search
        package_path = "{context_path}/{import_file}".format(context_path=context_path, import_file = import_file)
        module_path = "{package_path}.py".format(package_path = package_path)
            
        node = None
        # Check if import is a Python file within a local module
        if utils.is_valid_module(module_path):
            normal_path = utils.get_normal_path(module_path)
            node = Node(name=context_dotted_name, ID=normal_path, alias=alias)
            self.graph[file.filepath].add(node)
            self.process_file(normal_path)

        # Check if import is (possibly) an attribute of a local module
        elif utils.is_valid_module(context_module_path):
            normal_path = utils.get_normal_path(context_module_path)
            node = Node(name=context, ID=normal_path, alias=alias)
            self.graph[file.filepath].add(node)
            self.process_file(normal_path)

        # Check if import is a local package
        elif utils.is_valid_package(package_path):
            normal_path = utils.get_normal_path(package_path)
            self.process_dir(file.filepath, context_dotted_name, normal_path)

        # Check if import is (possibly) an attribute of a local module (in the __init__.py file)
        elif utils.is_valid_module(context_init_path):
            normal_path = utils.get_normal_path(context_init_path)
            node = Node(name=context_dotted_name, ID=normal_path, alias=alias)
            self.graph[file.filepath].add(node)
            self.process_file(normal_path)

        # Check if import is a library module
        elif self.is_library(context_dotted_name):
            label = "stdlib" if self.is_stdlib(context_dotted_name) else "site_package"
            node = Node(name=context_dotted_name, ID=context_dotted_name, labels=[label], alias=alias)
            self.graph[context_dotted_name] = set()
            self.graph[file.filepath].add(node)

        # Check if import is an attribute of a library
        elif self.is_library(context):
            label = "stdlib" if self.is_stdlib(context) else "site_package"
            node = Node(name=context, ID=context, labels=[label], alias=alias)
            self.graph[context] = set()
            self.graph[file.filepath].add(node)

        # Handle case where import is neither recognized as a local file nor a known library
        else:
            if self.config.resolve_all_imports:
                logging.warning("Cannot resolve import {context_dotted_name} in file {filepath}.".format(context_dotted_name=context_dotted_name, filepath=file.filepath))
                import_name = context if context else dotted_name
                node = Node(name=import_name, ID=import_name, labels=[], alias=alias)
                self.graph[import_name] = set()
                self.graph[file.filepath].add(node)

            else:
                logging.error("Cannot resolve import {context_dotted_name} in file {filepath}.".format(context_dotted_name=context_dotted_name, filepath=file.filepath))

        return node
              
    ## Extract alias and handle import normally
    def handle_aliased_import(self, file: File, tree_sitter_node: TreeSitterNode, context: TreeSitterNode) -> Node:
        dotted_name_node, as_node, alias_node = tree_sitter_node.children
        alias = self.extract_string(alias_node, file.lines)
        return self.handle_dotted_name(file, dotted_name_node, context, alias=alias)

    ## Treat a wildcard import like a normal import 
    def handle_wildcard_import(self, file: File, tree_sitter_node: TreeSitterNode, context: TreeSitterNode) -> Node:
        self.handle_dotted_name(file, context, None, alias="")
        return None

    ## Handle each kind of import differently 
    def delegate_import(self, file: File, import_children: list, context: TreeSitterNode) -> list:
        import_nodes = []
        for node in import_children:
            if node.type in self.import_delegate:
                import_node = self.import_delegate[node.type](file, node, context)
                import_nodes.append(import_node)
            else:
                logging.error("Unknown node type {nodetype} within import statement".format(nodetype=node.type))
        return import_nodes

    ## Handle an import statement by differentiating between normal imports and imports 'from'
    def handle_import(self, file: File, tree_sitter_node: TreeSitterNode) -> list:
        ## If node is an import statement
        context = None
        import_children = tree_sitter_node.children

        # If node is an import from statement, define context and adjust children
        if tree_sitter_node.type == "import_from_statement":
            context = import_children[1]
            import_children = import_children[2:]

        return self.delegate_import(file, import_children, context)

    ## DFS through subtree and check if every identifier is one of the imports, remove from unused map if so
    def handle_unknown_token(self, file: File, tree_sitter_node: TreeSitterNode, imports: dict):
        used_imports = set()
        if tree_sitter_node.type == "identifier":
            identifier = self.extract_string(tree_sitter_node, file.lines)
            if identifier in imports:
                used_imports.add(identifier)

        for child in tree_sitter_node.children:
            used_child_imports = self.handle_unknown_token(file, child, imports)
            used_imports = used_imports.union(used_child_imports)

        return used_imports

    ## Recursively process all files and subdirectories within given directory
    def process_dir(self, src_filepath: str, context_dotted_name: str, dirpath: str):
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
    def process_file(self, filepath: str):
        # Ensure that we don't revisit files
        if filepath in self.graph:
            return

        logging.info("[DependencyAnalyzer::process_file] Processing File {file}.".format(file=filepath))
        
        # Iterate through the parse tree and process any imports
        self.graph[filepath] = set()
        tree, lines = self.parser.parse_file(filepath)
        file = File(filepath, lines)
        
        imports = {}
        used_imports = set()
        for node in tree.root_node.children:
            if self.is_import(node):
                import_node_list = self.handle_import(file, node)
                for import_node in import_node_list:
                    if import_node:
                        imports[import_node.alias] = import_node
            elif self.config.find_unused:
                token_used_imports = self.handle_unknown_token(file, node, imports)
                used_imports = used_imports.union(token_used_imports)

        if self.config.find_unused:
            for dependency in self.graph[filepath]:
                #print("skip", dependency.ID, filepath)
                alias = dependency.alias
                if alias and (alias in imports) and (alias not in used_imports) and (dependency.ID == imports[alias].ID):
                    #print(alias, dependency.ID, filepath, dependency)
                    dependency.labels = ["unused"]


    ## Generates dependency graph for given directory and filepath, returns whether or not call was successful
    def process(self, dirpath: str, filepath: str) -> bool:
        self.reset() # Clear dependency graph 
        
        # Parse directory contents
        if not utils.directory_contains_file(dirpath, filepath):
            logging.error("File {filepath} is not contained within directory {dirpath}.".format(filepath=filepath, dirpath=dirpath))
            return False

        self.process_file(filepath)
        return True

    ## DFS through dependency graph to generate all paths
    def dependency_paths(self, filepath: str) -> set:
        # Ensure that filepath is valid
        dependencies = set()
        if filepath not in self.graph:
            return dependencies

        # Initialize root node as filepath
        name = utils.extract_filename(filepath)
        root = Node(name=name, ID=filepath)
        context = [root]
        visited = set()

        ## DFS through graph and add path to dependencies list each time we encounter a leaf
        def visit(u: TreeSitterNode):
            if self.graph[u.ID] and u.ID not in visited:
                visited.add(u.ID)
                for v in self.graph[u.ID]:
                    context.append(v)
                    visit(v)
                    context.pop()
            else:
                dependencies.add(tuple(context))
            
        visit(root)
        return dependencies

    ## Generate all dependency paths and pretty print them
    def print_dependency_paths(self, filepath: str):
        dependency_paths = self.dependency_paths(filepath)
        for path in dependency_paths:
            print(" "*4 + " <- ".join(map(str, path[::-1])))

    ## Print dependency graph
    def print_graph(self):
        for node in self.graph:
            print(node)
            for adj in self.graph[node]:
                print(" "*4 + str(adj))

    ## Display dependency graph using graphviz
    def render_graph(self):
        dot = graphviz.Digraph(comment='Dependency Graph')
        for node in self.graph:
            dot.node(node)
            edgeset = set()
            for adj in self.graph[node]:
                if adj.ID not in edgeset:
                    dot.edge(node, adj.ID)
                    edgeset.add(adj.ID)
        dot.render('dependency_graph', view=True)

    ## Produce and display dependency graph for a given file
    def run(self, dirpath: str, filepath: str):
        success = self.process(dirpath, filepath)
        self.print_dependency_paths(filepath)
        if success and self.config.render_graph:
            self.render_graph()

