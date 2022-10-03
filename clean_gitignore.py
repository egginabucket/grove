#!/usr/bin/python3

# Simple gitignore cleaner
# You can now mindlessly copy+paste from templates to your heart's desire!
# https://gist.github.com/YeemBoi/c397c4f50f6ede4a25a9585ea1116f6f/edit

import sys
import re

comment = re.compile('#+ .+')
has_content = lambda line: bool(len(line)) and not comment.fullmatch(line)

def main():
	if len(sys.argv) > 1:
		gitignore = sys.argv[1]
	else:
		gitignore = '.gitignore'
	
	lines = []
	with open(gitignore, 'rt') as f:
		for line in f:
			line = line.strip()
			# Skip repeating lines (usually gaps created by other skips)
			if len(lines) and line == lines[-1]:
				continue

			# Skip obviously redundant lines
			if has_content(line) and line in lines:
				strip_end = 0
				# Trim other lines (comments) made irrevelant by skip
				for i, prev_line in enumerate(reversed(lines)):
					if has_content(prev_line):
						break
					strip_end = i
				if strip_end:
					lines = lines[: -strip_end]
				continue

			lines.append(line)

	with open(gitignore, 'wt') as f:
		f.writelines([line + '\r\n' for line in lines])

if __name__ == '__main__':
	main()
