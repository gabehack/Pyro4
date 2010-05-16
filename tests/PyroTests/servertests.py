from __future__ import with_statement
import unittest
import Pyro.config
import Pyro.core
import Pyro.errors
import threading, time, os

# tests that require a running Pyro server (daemon)
# the server part here is not using a timeout setting.

class MyThing(object):
    def __init__(self):
        self.dictionary={"number":42}
    def getDict(self):
        return self.dictionary
    def multiply(self,x,y):
        return x*y
    def ping(self):
        pass
    def delay(self, delay):
        time.sleep(delay)
        return "slept %d seconds" % delay

class DaemonLoopThread(threading.Thread):
    def __init__(self, pyrodaemon):
        super(DaemonLoopThread,self).__init__()
        self.setDaemon(True)
        self.pyrodaemon=pyrodaemon
        self.running=threading.Event()
        self.running.clear()
    def run(self):
        self.running.set()
        self.pyrodaemon.requestLoop()
        
class ServerTestsThreadNoTimeout(unittest.TestCase):
    SERVERTYPE="thread"
    COMMTIMEOUT=None
    def setUp(self):
        Pyro.config.SERVERTYPE=self.SERVERTYPE
        Pyro.config.COMMTIMEOUT=self.COMMTIMEOUT
        self.daemon=Pyro.core.Daemon(port=0)
        obj=MyThing()
        uri=self.daemon.register(obj, "something")
        self.objectUri=uri
        self.daemonthread=DaemonLoopThread(self.daemon)
        self.daemonthread.start()
        self.daemonthread.running.wait()
    def tearDown(self):
        time.sleep(0.05)
        self.daemon.shutdown()
        self.daemonthread.join()
        Pyro.config.SERVERTYPE="thread"
        Pyro.config.COMMTIMEOUT=None

    def testNoDottedNames(self):
        Pyro.config.DOTTEDNAMES=False
        with Pyro.core.Proxy(self.objectUri) as p:
            self.assertEqual(55,p.multiply(5,11))
            x=p.getDict()
            self.assertEqual({"number":42}, x)
            try:
                p.dictionary.update({"more":666})     # should fail with DOTTEDNAMES=False (the default)
                self.fail("expected AttributeError")
            except AttributeError:
                pass
            x=p.getDict()
            self.assertEqual({"number":42}, x)

    def testDottedNames(self):
        try:
            Pyro.config.DOTTEDNAMES=True
            with Pyro.core.Proxy(self.objectUri) as p:
                self.assertEqual(55,p.multiply(5,11))
                x=p.getDict()
                self.assertEqual({"number":42}, x)
                p.dictionary.update({"more":666})    # updating it remotely should work with DOTTEDNAMES=True
                x=p.getDict()
                self.assertEqual({"number":42, "more":666}, x)  # eek, it got updated!
        finally:
            Pyro.config.DOTTEDNAMES=False

    def testConnectionStuff(self):
        p1=Pyro.core.Proxy(self.objectUri)
        p2=Pyro.core.Proxy(self.objectUri)
        self.assertTrue(p1._pyroConnection is None)
        self.assertTrue(p2._pyroConnection is None)
        p1.ping()
        p2.ping()
        x=p1.multiply(11,5)
        x=p2.multiply(11,5)
        self.assertTrue(p1._pyroConnection is not None)
        self.assertTrue(p2._pyroConnection is not None)
        p1._pyroRelease()
        p1._pyroRelease()
        p2._pyroRelease()
        p2._pyroRelease()
        self.assertTrue(p1._pyroConnection is None)
        self.assertTrue(p2._pyroConnection is None)
        p1._pyroBind()
        x=p1.multiply(11,5)
        x=p2.multiply(11,5)
        self.assertTrue(p1._pyroConnection is not None)
        self.assertTrue(p2._pyroConnection is not None)
        self.assertEqual("PYRO",p1._pyroUri.protocol)
        self.assertEqual("PYRO",p2._pyroUri.protocol)
        p1._pyroRelease()
        p2._pyroRelease()

    def testReconnect(self):
        with Pyro.core.Proxy(self.objectUri) as p:
            self.assertTrue(p._pyroConnection is None)
            p._pyroReconnect(tries=100)
            self.assertTrue(p._pyroConnection is not None)
        self.assertTrue(p._pyroConnection is None)
    
    def testOneway(self):
        with Pyro.core.Proxy(self.objectUri) as p:
            self.assertEquals(55, p.multiply(5,11))
            p._pyroOneway.add("multiply")
            self.assertEquals(None, p.multiply(5,11))
            self.assertEquals(None, p.multiply(5,11))
            self.assertEquals(None, p.multiply(5,11))
            p._pyroOneway.remove("multiply")
            self.assertEquals(55, p.multiply(5,11))
            self.assertEquals(55, p.multiply(5,11))
            self.assertEquals(55, p.multiply(5,11))
            # check nonexisting method behavoir
            self.assertRaises(AttributeError, p.nonexisting)
            p._pyroOneway.add("nonexisting")
            # now it shouldn't fail because of oneway semantics
            p.nonexisting()
            
    def testOnewayDelayed(self):
        try:
            with Pyro.core.Proxy(self.objectUri) as p:
                Pyro.config.ONEWAY_THREADED=True   # the default
                p._pyroOneway.add("delay")
                now=time.time()
                p.delay(1)  # oneway so we should continue right away
                self.assertTrue(time.time()-now < 0.2, "delay should be running as oneway")
                now=time.time()
                self.assertEquals(55,p.multiply(5,11), "expected a normal result from a non-oneway call")
                self.assertTrue(time.time()-now < 0.2, "delay should be running in its own thread")
                # make oneway calls run in the server thread
                # we can change the config here and the server will pick it up on the fly
                Pyro.config.ONEWAY_THREADED=False   
                now=time.time()
                p.delay(1)  # oneway so we should continue right away
                self.assertTrue(time.time()-now < 0.2, "delay should be running as oneway")
                now=time.time()
                self.assertEquals(55,p.multiply(5,11), "expected a normal result from a non-oneway call")
                self.assertFalse(time.time()-now < 0.2, "delay should be running in the server thread")
        finally:
            Pyro.config.ONEWAY_THREADED=True   # back to normal

    def testOnewayOnClass(self):
        class ProxyWithOneway(Pyro.core.Proxy):
            def __init__(self, arg):
                super(ProxyWithOneway,self).__init__(arg)
                self._pyroOneway=["multiply"]   # set is faster but don't care for this test
        with ProxyWithOneway(self.objectUri) as p:
            self.assertEquals(None, p.multiply(5,11))
            p._pyroOneway=[]   # empty set is better but don't care in this test
            self.assertEquals(55, p.multiply(5,11))

    def testSerializeConnected(self):
        # online serialization tests
        ser=Pyro.util.Serializer()
        proxy=Pyro.core.Proxy(self.objectUri)
        proxy._pyroBind()
        self.assertFalse(proxy._pyroConnection is None)
        p,_=ser.serialize(proxy)
        proxy2=ser.deserialize(p)
        self.assertTrue(proxy2._pyroConnection is None)
        self.assertFalse(proxy._pyroConnection is None)
        self.assertEqual(proxy2._pyroUri, proxy._pyroUri)
        self.assertEqual(proxy2._pyroSerializer, proxy._pyroSerializer)
        proxy2._pyroBind()
        self.assertFalse(proxy2._pyroConnection is None)
        self.assertFalse(proxy2._pyroConnection is proxy._pyroConnection)
        proxy._pyroRelease()
        proxy2._pyroRelease()
        self.assertTrue(proxy._pyroConnection is None)
        self.assertTrue(proxy2._pyroConnection is None)
        proxy.ping()
        proxy2.ping()
        # try copying a connected proxy
        import copy
        proxy3=copy.copy(proxy)
        self.assertTrue(proxy3._pyroConnection is None)
        self.assertFalse(proxy._pyroConnection is None)
        self.assertEqual(proxy3._pyroUri, proxy._pyroUri)
        self.assertFalse(proxy3._pyroUri is proxy._pyroUri)
        self.assertEqual(proxy3._pyroSerializer, proxy._pyroSerializer)        
        proxy._pyroRelease()
        proxy2._pyroRelease()
        proxy3._pyroRelease()

    def testTimeoutCall(self):
        try:
            Pyro.config.COMMTIMEOUT=None
            with Pyro.core.Proxy(self.objectUri) as p:
                p.ping()
                start=time.time()
                p.delay(1)
                duration=time.time()-start
                self.assertAlmostEqual(1.0, duration, 1)
                p._pyroTimeout=0.5
                start=time.time()
                self.assertRaises(Pyro.errors.TimeoutError, p.delay, 2)
                duration=time.time()-start
                self.assertTrue(duration<2.0)
            Pyro.config.COMMTIMEOUT=0.5
            with Pyro.core.Proxy(self.objectUri) as p:
                p.ping()
                start=time.time()
                self.assertRaises(Pyro.errors.TimeoutError, p.delay, 2)
                duration=time.time()-start
                self.assertTrue(duration<2.0)
                p._pyroTimeout=None
                start=time.time()
                p.delay(1)
                duration=time.time()-start
                self.assertTrue(0.9<duration<1.9)
        finally:
            Pyro.config.COMMTIMEOUT=None

    def testTimeoutConnect(self):
        # set up a unresponsive daemon
        with Pyro.core.Daemon(port=0) as d:
            obj=MyThing()
            uri=d.register(obj)
            # we're not going to start the daemon's event loop
            p=Pyro.core.Proxy(uri)
            p._pyroTimeout=0.2
            start=time.time()
            self.assertRaises(Pyro.errors.TimeoutError, p.ping)
            duration=time.time()-start
            self.assertTrue(duration<3.0)
            
    def testProxySharing(self):
        class SharedProxyThread(threading.Thread):
            def __init__(self, proxy):
                super(SharedProxyThread,self).__init__()
                self.proxy=proxy
                self.terminate=False
                self.error=False
                self.setDaemon(True)
            def run(self):
                while not self.terminate:
                    try:
                        reply=self.proxy.multiply(5,11)
                        assert reply==55
                    except Exception:
                        self.error=True
                        self.terminate=True
        with Pyro.core.Proxy(self.objectUri) as p:
            threads=[]
            for i in range(5):
                t=SharedProxyThread(p)
                threads.append(t)
                t.start()
            time.sleep(1)
            for t in threads:
                t.terminate=True
                t.join()
            for t in threads:
                self.assertFalse(t.error, "all threads should report no errors") 

if os.name!="java":
    class ServerTestsSelectNoTimeout(ServerTestsThreadNoTimeout):
        SERVERTYPE="select"
        COMMTIMEOUT=None

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
