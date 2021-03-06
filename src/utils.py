import distutils.sysconfig as sysconfig
import os

## Checks if directory path is valid
def is_valid_dir(dirpath):
	return os.path.isdir(dirpath)

## Checks if file path is valid
def is_valid_file(filepath):
	return os.path.isfile(filepath)

## Checks if file path is valid python
def is_valid_module(filepath):
	return os.path.isfile(filepath) and filepath[-3:] == ".py"

## Checks if folder path is valid python
def is_valid_package(package_path):
	init_filepath = "{package_path}/__init__.py".format(package_path=package_path)
	return os.path.exists(package_path) and os.path.isfile(init_filepath)

## Returns contents of given directory
def get_directory_contents(dirpath):
	return os.scandir(dirpath)

## Process dotted name to yield relative path
def get_path(dotted_name):
	stripped = dotted_name.strip('.')
	dots = len(dotted_name) - len(stripped) - 1
	prefix = [".." for i in range(0, dots)]
	suffix = stripped.split(".")
	return "." if dotted_name == "." else "/".join(prefix + suffix)

## Normalizes path to omit unnecessary characters
def get_normal_path(path):
	return os.path.normpath(path)

## Parse filepath to yield filename
def extract_filename(filepath):
	return filepath.split("/")[-1].split(".")[0]

## Get parent directory for given file
def extract_parent_directory(filepath):
	return os.path.dirname(filepath)

## Check if given file is contained within given directory
def directory_contains_file(dirpath, filepath):
	directory_files = get_directory_files(dirpath)
	return filepath in directory_files

## Returns a list of file paths within the specified directory
def get_directory_files(dirpath):
	files = []
	for entry in os.scandir(dirpath):
		if entry.is_file():
			files.append(entry.path)
		else:
			files += get_directory_files(entry.path)
	return files

## --This function was taken from stack overflow--
## Get a list of available libraries 
def get_libraries():
	lib = set()
	std_lib = sysconfig.get_python_lib(standard_lib=True)
	for top, dirs, files in os.walk(std_lib):
	    for name in files:
	        if name != '__init__.py' and name[-3:] == '.py':
	        	lib.add(name)
	return lib