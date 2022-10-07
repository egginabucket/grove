#!/usr/bin/python3
import sys

def main():
    if len(sys.argv) < 2:
        raise ValueError('Filename required')
    filename = sys.argv[1]
    if '.' not in filename:
        filename += '.yaml'
    with open(filename, 'rt') as f:
        lines = f.readlines()
    with open(filename, 'wt') as f:
        f.writelines(sorted(lines))

if __name__ == '__main__':
    main()
