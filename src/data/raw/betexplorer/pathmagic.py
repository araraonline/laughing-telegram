import os
import sys

# function aliases
dn = os.path.dirname
ab = os.path.abspath

# add project directory to path
base_dir = dn(dn(dn(dn(dn(ab(__file__))))))
sys.path.insert(0, base_dir)
