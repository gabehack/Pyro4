try:
    import queue
except ImportError:
    import Queue as queue
import Pyro4

# apply Pyro4.config settings
from dispatcher_config import *

_pyro4_current_context = Pyro4.current_context

class DispatcherQueue(object):
    def __init__(self):
        self.workqueue = queue.Queue()
        self.resultqueue = queue.Queue()

    @Pyro4.oneway
    def putWork_standard(self, item):
        self.workqueue.put(item)
    @Pyro4.oneway
    def putWork_byannotation(self):
        self.workqueue.put(
            _pyro4_current_context.annotations.pop('XPUT'))

    def getWork_standard(self):
        return self.workqueue.get(block=True, timeout=None)
    def getWork_byannotation(self):
        _pyro4_current_context.annotations['XGET'] = \
            self.workqueue.get(block=True, timeout=None)

    @Pyro4.oneway
    def putResult_standard(self, item):
        self.resultqueue.put(item)
    @Pyro4.oneway
    def putResult_byannotation(self):
        self.resultqueue.put(
            _pyro4_current_context.annotations.pop('XPUT'))

    def getResult_standard(self):
        return self.resultqueue.get(block=True, timeout=None)
    def getResult_byannotation(self):
        _pyro4_current_context.annotations['XGET'] = \
            self.resultqueue.get(block=True, timeout=None)

class CustomDispatcherDaemon(Pyro4.Daemon):
    def annotations(self):
        annotations = super(CustomDispatcherDaemon, self).annotations()
        if 'XGET' in _pyro4_current_context.annotations:
            annotations['XGET'] = _pyro4_current_context.annotations.pop('XGET')
        return annotations

# main program
Pyro4.Daemon.serveSimple(
    {DispatcherQueue(): 'example.distributed.dispatcher'},
    daemon=CustomDispatcherDaemon())
