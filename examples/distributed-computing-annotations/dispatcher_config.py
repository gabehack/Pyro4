import inspect
try:
    import cPickle as pickle
except:
    import pickle
import json
import serpent
import marshal
import Pyro4

# This setting controls whether or not we use
# the standard dispatcher model or the experimental
# annotation-based dispatcher model (be sure to
# restart the dispatcher and worker(s) if this
# or the config settings below are updated.
use_annotation_based_dispatcher = False

# Note if this option is set to True, you will need to apply the
# (experimental) patch to Pyro4.core that attempts to transfer the
# parent thread's local 'current_context' into the child's
Pyro4.config.ONEWAY_THREADED = False
Pyro4.config.SERIALIZERS_ACCEPTED = set(['json',
                                         'marshal',
                                         'serpent',
                                         'pickle'])
Pyro4.config.SERIALIZER = 'serpent'

serializer = locals()[Pyro4.config.SERIALIZER]
if not use_annotation_based_dispatcher:

    # use the standard dispatcher behavior
    class TestDispatcherProxy(Pyro4.Proxy):
        def __init__(self, *args, **kwds):
            super(TestDispatcherProxy, self).__init__(*args, **kwds)
            # mock behavior of annotation based proxy class
            self._pyroBind()
        def putWork(self, item):
            self.putWork_standard(item)
        def getWork(self):
            return self.getWork_standard()
        def putResult(self, item):
            self.putResult_standard(item)
        def getResult(self):
            return self.getResult_standard()

else:

    # use annotation based dispatcher behavior
    # (avoid intermediate de-serialization and re-serialization
    #  on the dispatcher)
    class TestDispatcherProxy(Pyro4.Proxy):

        def __init__(self, *args, **kwds):
            super(TestDispatcherProxy, self).__init__(*args, **kwds)
            self.__dict__['_put_item'] = None
            self.__dict__['_get_item'] = None
            # bind here so that we don't populate the annotation dict
            # with a serialized item during the binding procedure that
            # would occur during the first remote method call
            self._pyroBind()

        def putWork(self, item):
            self.__dict__['_put_item'] = serializer.dumps(item)
            self.putWork_byannotation()

        def getWork(self):
            self.getWork_byannotation()
            item = serializer.loads(self.__dict__['_get_item'])
            self.__dict__['_get_item'] = None
            return item

        def putResult(self, item):
            self.__dict__['_put_item'] = serializer.dumps(item)
            self.putResult_byannotation()

        def getResult(self):
            self.getResult_byannotation()
            item = serializer.loads(self.__dict__['_get_item'])
            self.__dict__['_get_item'] = None
            return item

        def _pyroAnnotations(self):
            annotations = \
                super(TestDispatcherProxy, self)._pyroAnnotations()
            if self.__dict__['_put_item'] is not None:
                annotations['XPUT'] = self.__dict__['_put_item']
                self.__dict__['_put_item'] = None
            return annotations

        def _pyroResponseAnnotations(self, annotations, msgtype):
            super(TestDispatcherProxy, self).\
                _pyroResponseAnnotations(annotations, msgtype)
            self.__dict__['_get_item'] = annotations.get('XGET')
