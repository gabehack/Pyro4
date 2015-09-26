import os
import socket

# import proxy type and apply Pyro4.config settings
from dispatcher_config import *

WORKERNAME = "Worker_%d@%s" % (os.getpid(), socket.gethostname())
def main():
    print("This is worker %s" % (str(WORKERNAME)))
    print("getting work from dispatcher.")
    dispatcher = TestDispatcherProxy(
        "PYRONAME:example.distributed.dispatcher")
    while 1:
        item = dispatcher.getWork()
        dispatcher.putResult(item)

if __name__ == "__main__":
    main()
