from __future__ import print_function, division
import os

# Pygame prints lots of internal debug, so redirect stdout to /dev/null
stdout_fd = os.dup(1)
stdout = os.fdopen(stdout_fd, "w")
null_fd = os.open("/dev/null", os.O_WRONLY)
os.dup2(null_fd, 1)

_print = print
def print(*a, **kw):
	_print(*a, file=stdout, **kw)
