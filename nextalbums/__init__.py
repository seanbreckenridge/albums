import os
import sys

# !!!!!!!!!!!!!!!!!!!!!!!!
# THIS CANT BE INSTALLED AS A REGULAR PACKAGE
# since this acts on data files that I'd rather keep part of this
# package, it has to be installed as an editable package
# like:
# python3 -m pip install install --editable ~/Repos/albums [the root dir with the setup.py file]

root_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.path.pardir))

sys.path.insert(0, root_dir)

import settings as SETTINGS

