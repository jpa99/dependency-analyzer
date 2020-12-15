import distutils.sysconfig as sysconfig
import os

## Checks if directory path is valid
def is_valid_dir(dirpath):
	return os.path.isdir(dirpath)

## Checks if file path is valid
def is_valid_file(filepath):
	return os.path.isfile(filepath)

## Checks if file path is valid python
def is_valid_python_file(filepath):
	return os.path.isfile(filepath) and filepath[-3:] == ".py"

def extract_parent_directory(filepath):
	return os.path.dirname(filepath)


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
def get_packages():
	lib = set()
	std_lib = sysconfig.get_python_lib(standard_lib=True)
	for top, dirs, files in os.walk(std_lib):
	    for name in files:
	        if name != '__init__.py' and name[-3:] == '.py':
	        	lib.add(name)
	return lib