import os

def print_tree(startpath, exclude_dirs=None):
    if exclude_dirs is None:
        exclude_dirs = {'.git', '__pycache__', '.venv', 'venv', 'node_modules', '.pytest_cache'}
    
    for root, dirs, files in os.walk(startpath):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        level = root.replace(startpath, '').count(os.sep)
        indent = ' ' * 4 * (level)
        print('{}{}/'.format(indent, os.path.basename(root)))
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            print('{}{}'.format(subindent, f))

print_tree('.')
