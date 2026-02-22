import sys

# textual_image queries sixel terminal support at import time via sys.stdin.buffer.fileno(),
# which fails when pytest replaces stdin with a pseudofile. Restore the real stdin first.
sys.stdin = sys.__stdin__
