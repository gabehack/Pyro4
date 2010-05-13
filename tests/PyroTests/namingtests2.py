from __future__ import with_statement
import unittest
import sys, StringIO
import Pyro.naming
import Pyro.nsc
import Pyro.socketutil
from Pyro.errors import NamingError,PyroError

# offline name-server tests

class OfflineNameServerTests(unittest.TestCase):
    def testRegister(self):
        ns=Pyro.naming.NameServer()
        ns.ping()
        ns.register("test.object1","PYRO:111111@host.com:4444")
        ns.register("test.object2","PYRO:222222@host.com:4444")
        ns.register("test.object3","PYRO:333333@host.com:4444")
        ns.register("test.sub.objectA",Pyro.core.PyroURI("PYRO:AAAAAA@host.com:4444"))
        ns.register("test.sub.objectB",Pyro.core.PyroURI("PYRO:BBBBBB@host.com:4444"))

        self.assertRaises(NamingError, ns.register, "test.object1", "PYRO:X@Y:5555")
        self.assertRaises(TypeError, ns.register, None, None)
        self.assertRaises(TypeError, ns.register, 4444, 4444)
        self.assertRaises(TypeError, ns.register, "test.wrongtype", 4444)
        self.assertRaises(TypeError, ns.register, 4444, "PYRO:X@Y:5555")

        self.assertRaises(NamingError, ns.lookup, "unknown_object")
        
        uri=ns.lookup("test.object3")
        self.assertEqual(Pyro.core.PyroURI("PYRO:333333@host.com:4444"), uri)   # lookup always returns PyroURI
        ns.remove("unknown_object")
        ns.remove("test.object1")
        ns.remove("test.object2")
        ns.remove("test.object3")
        all=ns.list()
        self.assertEqual(2, len(all))  # 2 leftover objects

        self.assertRaises(PyroError, ns.register, "test.nonurivalue", "THISVALUEISNOTANURI")

    def testUnicodeNames(self):
        ns=Pyro.naming.NameServer()
        uri=Pyro.core.PyroURI(u"PYRO:unicode\u20ac@host:5555")
        ns.register(u"unicodename\u20ac", uri)
        x=ns.lookup(u"unicodename\u20ac")
        self.assertEqual(uri, x)

    def testList(self):
        ns=Pyro.naming.NameServer()
        ns.register("test.objects.1","PYRONAME:something1")
        ns.register("test.objects.2","PYRONAME:something2")
        ns.register("test.objects.3","PYRONAME:something3")
        ns.register("test.other.a","PYRONAME:somethingA")
        ns.register("test.other.b","PYRONAME:somethingB")
        ns.register("test.other.c","PYRONAME:somethingC")
        ns.register("entirely.else","PYRONAME:meh")
        objects=ns.list()
        self.assertEqual(7,len(objects))
        objects=ns.list(prefix="nothing")
        self.assertEqual(0,len(objects))
        objects=ns.list(prefix="test.")
        self.assertEqual(6,len(objects))
        objects=ns.list(regex=r".+other..")
        self.assertEqual(3,len(objects))
        self.assertTrue("test.other.a" in objects)
        self.assertEqual("PYRONAME:somethingA", objects["test.other.a"])
        objects=ns.list(regex=r"\d\d\d\d\d\d\d\d\d\d")
        self.assertEqual(0,len(objects))
        self.assertRaises(NamingError, ns.list, regex="((((((broken")

    def testRefuseDotted(self):
        try:
            Pyro.config.DOTTEDNAMES=True
            ns=Pyro.naming.NameServerDaemon(port=0)
            self.fail("should refuse to create name server")
        except PyroError:
            pass
        finally:
            Pyro.config.DOTTEDNAMES=False
        
    def testNameserverWithStmt(self):
        ns=Pyro.naming.NameServerDaemon(port=0)
        self.assertFalse(ns.nameserver is None)
        ns.close()
        self.assertTrue(ns.nameserver is None)
        with Pyro.naming.NameServerDaemon(port=0) as ns:
            self.assertFalse(ns.nameserver is None)
            pass
        self.assertTrue(ns.nameserver is None)
        try:
            with Pyro.naming.NameServerDaemon(port=0) as ns:
                self.assertFalse(ns.nameserver is None)
                print 1//0 # cause an error
            self.fail("expected error")
        except ZeroDivisionError: 
            pass
        self.assertTrue(ns.nameserver is None)
        ns=Pyro.naming.NameServerDaemon(port=0)
        with ns:
            pass
        try:
            with ns:
                pass
            self.fail("expected error")
        except PyroError:
            # you cannot re-use a name server object in multiple with statements
            pass
        ns.close()

    def testStartNSfunc(self):
        uri1,ns1,bc1=Pyro.naming.startNS(port=0, enableBroadcast=False)
        uri2,ns2,bc2=Pyro.naming.startNS(port=0, enableBroadcast=True)
        self.assertTrue(isinstance(uri1, Pyro.core.PyroURI))
        self.assertTrue(isinstance(ns1, Pyro.naming.NameServerDaemon))
        self.assertTrue(bc1 is None)
        self.assertTrue(isinstance(bc2, Pyro.naming.BroadcastServer))
        sock=bc2.sock
        self.assertTrue(hasattr(sock,"fileno"))
        func=bc2.processRequest
        ns1.close()
        ns2.close()
        bc2.close()
    
    def testOwnloopBasics(self):
        uri1,ns1,bc1=Pyro.naming.startNS(port=0, enableBroadcast=True)
        self.assertTrue(ns1.fileno() > 0)
        self.assertTrue(bc1.fileno() > 0)
        _,_,_=Pyro.socketutil.selectfunction([ns1, bc1],[],[],0.1)

    def testNSmain(self):
        oldstdout=sys.stdout
        oldstderr=sys.stderr
        try:
            sys.stdout=StringIO.StringIO()
            sys.stderr=StringIO.StringIO()
            self.assertRaises(SystemExit, Pyro.naming.main, ["--invalidarg"])
            self.assertTrue("no such option" in sys.stderr.getvalue())
            sys.stderr.truncate(0)
            sys.stdout.truncate(0)
            self.assertRaises(SystemExit, Pyro.naming.main, ["-h"])
            self.assertTrue("show this help message" in sys.stdout.getvalue())
        finally:
            sys.stdout=oldstdout
            sys.stderr=oldstderr

    def testNSCmain(self):
        oldstdout=sys.stdout
        oldstderr=sys.stderr
        try:
            sys.stdout=StringIO.StringIO()
            sys.stderr=StringIO.StringIO()
            self.assertRaises(SystemExit, Pyro.nsc.main, ["--invalidarg"])
            self.assertTrue("no such option" in sys.stderr.getvalue())
            sys.stderr.truncate(0)
            sys.stdout.truncate(0)
            self.assertRaises(SystemExit, Pyro.nsc.main, ["-h"])
            self.assertTrue("show this help message" in sys.stdout.getvalue())
        finally:
            sys.stdout=oldstdout
            sys.stderr=oldstderr
            

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
