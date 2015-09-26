This is the original distributed computing example (simplified) to
test potential performance gains from skipping intermediate
de-serialization and re-serialization of tasks that occurs on the
dispatcher when work/result items flow between client and worker.

This is implemented using a custom dispatcher proxy and daemon. The
custom dispatcher proxy performs the work/result item
(de)serialization outside of the remote method call and
(extracts)inserts the serialized object (from)into the remote method
call using the annotations dict. The custom daemon inserts the
serialized work/result item into the queue by extracting it from the
thread-local annotations dict (rather than through the function
argument).  Similarly, work/result requests are handled by extracting
an item from the queue and inserting it into the thread-local
annotations dict, which the overloaded annotations() Daemon method
will pull from.

This implementation is currently limited by the Pyro4 message header
size. The serialized work/result items must be small enough to fit in
this header. Hoping the Pyro4 developer(s) have a smarter way to
inject this sort of functionality.

One can adjust the WorkItem type and size in client.py. The serializer
to use and whether or not to disable the annotation-based dispatcher
functionality can be set in dispatcher_config.py.
