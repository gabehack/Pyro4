import time

# import proxy type and apply Pyro4.config settings
from dispatcher_config import *

NUMBER_OF_ITEMS = 800
# When using the annotation-based dispatcher, if we make the WorkItem
# any larger, we quickly run into the size limit on the message header
# and we get an error (this is currently a limitation of the
# annotation based approach we are testing)
WorkItem = dict((str(i),i) for i in range(1000))

def main():
    with TestDispatcherProxy(
            "PYRONAME:example.distributed.dispatcher") as dispatcher:
        start = time.time()
        placework(dispatcher)
        print("Time to place work: %s"
              % (time.time()-start))
        collectresults(dispatcher)
        print("Total time: %s "
              % (time.time()-start))

def placework(dispatcher):
    print("placing work items into dispatcher queue.")
    for i in range(NUMBER_OF_ITEMS):
        dispatcher.putWork(WorkItem)

def collectresults(dispatcher):
    print("getting results from dispatcher queue.")
    count = 0
    while count < NUMBER_OF_ITEMS:
        dispatcher.getResult()
        count += 1

if __name__ == "__main__":
    main()
