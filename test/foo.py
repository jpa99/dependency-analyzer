import bar
import sys
from bar import *
from include import baz as bz
from include.baz import goodbye as gb, hello as hl

bar.hello()
sys.exit(1)