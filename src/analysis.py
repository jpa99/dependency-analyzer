import utils
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
        self.import_handler = {
            "import": lambda: None,
            "dotted_name": self.handle_dotted_name,
            "aliased_import": self.handle_aliased_import,
            ",": lambda: None,
        }

    def refresh_packages(self):
        self.packages = utils.get_packages()

    def reset(self):
        self.refresh_packages()
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

    def extract_dotted_name(self, dotted_name_node, lines):
        children = dotted_name_node.children
        identifier_list = []
        for i in range(0, dotted_name_node.child_count, 2):
            assert children[i].start_point[0] == children[i].end_point[0] ## Assumption: no multi-line identifiers
            identifier = self.extract_string(children[i], lines)
            identifier_list.append(identifier)
        return ".".join(identifier_list)

    def handle_dotted_name(self, file, dotted_name_node, context="", alias=""):
        dotted_name = self.extract_dotted_name(dotted_name_node, file.lines)

        parent_dir_path = utils.extract_parent_directory(file.filepath)
        import_file = utils.get_path(dotted_name)
        
        context_string = "/{context}".format(context=utils.get_path(context)) if context else ""
        dotted_context = "{context}.".format(context=context) if context else ""
        context_dotted_name = "{dotted_context}{dotted_name}".format(dotted_context=dotted_context, dotted_name = dotted_name)

        context_path = "{parent_dir_path}{context_string}".format(parent_dir_path=parent_dir_path, context_string=context_string)
        context_module_path = "{context_path}.py".format(context_path = context_path)
        package_path = "{context_path}/{import_file}".format(parentdir = parent_dir_path, context_path=context_path, import_file = import_file)
        module_path = "{package_path}.py".format(package_path = package_path)

        # Check if full import name is valid
        if utils.is_valid_module(module_path):
            node = Node(name=context_dotted_name, ID=module_path, alias=alias)
            self.graph[file.filepath].add(node)
            self.process_file(module_path)

        # Check if context is a module and the import is an attribute
        elif utils.is_valid_module(context_module_path):
            node = Node(name=context, ID=context_module_path, alias=alias)
            self.graph[file.filepath].add(node)
            self.process_file(context_module_path)

        # Check if import is a package
        elif utils.is_valid_package(package_path):
            node = Node(name=context_dotted_name, ID=package_path, alias=alias)
            self.graph[file.filepath].add(node)
            self.process_dir(package_path)

        elif self.is_package(context_dotted_name):
            label = "stdlib" if self.is_stdlib(dotted_name) else "site_package"
            node = Node(name=dotted_name, ID=dotted_name, label=label, alias=alias)
            self.graph[dotted_name] = set()
            self.graph[file.filepath].add(node)
        else:
            print("INVALID IMPORT {},{}".format(dotted_name, package_path))
        
    def handle_aliased_import(self, file, aliased_import_node, context):
        dotted_name_node, as_node, alias_node = aliased_import_node.children
        alias = self.extract_string(alias_node, file.lines)
        self.handle_dotted_name(file, dotted_name_node, context, alias=alias)

    def handle_wildcard_import(self, file, context):
        self.handle_dotted_name(file, context)

    def handle_import(self, file, import_children, context=""):
        for child in import_children:
            if child.type == "import":
                pass
            elif child.type == "dotted_name":
                self.handle_dotted_name(file, child, context)
            elif child.type == "aliased_import":
                self.handle_aliased_import(file, child, context)
            elif child.type == "wildcard_inport":
                self.handle_wildcard_import(file, context)
            elif child.type in ",()":
                pass

            else:
                assert False

    def handle_import_from(self, file, import_from_children):
        dotted_name_node = import_from_children[1]
        context_name = self.extract_dotted_name(dotted_name_node, file.lines)
        self.handle_import(file, import_from_children[2:], context_name)

    def process_dir(self, dirpath):
        for entry in os.scandir(dirpath):
            entrypath = "{dirpath}/{entryname}".format(dirpath=dirpath, entryname=entry.name)
            if entry.is_dir() and utils.is_valid_package(entrypath):
                self.process_dir(entrypath)
            elif entry.is_valid_module(entrypath):
                self.process_file(entrypath)

    ## Generate dependency graph
    def process_file(self, filepath):
        # Ensure that we don't repeat
        if filepath in self.graph:
            return

        self.graph[filepath] = set()
        tree, lines = self.parser.parse_file(filepath)
        file = File(filepath, lines)
        import_statements = [node for node in tree.root_node.children if node.type == 'import_statement']
        import_from_statements = [node for node in tree.root_node.children if node.type == 'import_from_statement']
    
        for import_stmt in import_statements:
            self.handle_import(file, import_stmt.children)

        for import_from_stmt in import_from_statements:
            self.handle_import_from(file, import_from_stmt.children)

    def process(self, dirpath, filepath):
        self.reset()
        
        ## Parse directory contents
        if not utils.directory_contains_file(dirpath, filepath):
            print("INPUT ERROR: File not within directory")
            return

        self.process_file(filepath)


    def dependency_paths(self, filepath):
        dependencies = []
        if filepath not in self.graph:
            return dependencies

        name = utils.extract_filename(filepath)
        node = Node(name=name, ID=filepath)
        context = [node]
        def visit(u):
            if self.graph[u.ID]:
                for v in self.graph[u.ID]:
                    context.append(v)
                    visit(v)
                    context.pop()
            else:
                dependencies.append(list(context))

        visit(node)
        return dependencies

    def print_dependency_paths(self, filepath):
        dependency_paths = self.dependency_paths(filepath)
        for path in dependency_paths:
            print(" <- ".join(map(str, path[::-1])))

    def print_graph(self):
        for node in self.graph:
            print(node)
            for adj in self.graph[node]:
                print("    "+str(adj))

    def run(self, dirpath, filepath):
        self.process(dirpath, filepath)
        self.print_dependency_paths(filepath)

