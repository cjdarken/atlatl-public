import sys
sys.path.append("..")
from portabletorch import PortableTorch

portable = PortableTorch.load("mymodel")

portable.print()
portable.test()
