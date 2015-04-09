import unittest, webtest, endpoints
import uvalibrary_api
from google.appengine.api import memcache
from google.appengine.ext import ndb
from google.appengine.ext import testbed
from google.appengine.datastore import datastore_stub_util

class DemoTestCase(unittest.TestCase):

  def setUp(self):
    tb = testbed.Testbed()
    tb.setup_env(current_version_id='testbed.version') #needed because endpoints expects a . in this value
    tb.activate()
    tb.init_all_stubs()
    self.testbed = tb

  def tearDown(self):
    self.testbed.deactivate()

  def testEventuallyConsistentGlobalQueryResult(self):
    app = endpoints.api_server([uvalibrary_api.CatalogApi], restricted=False)
    testapp = webtest.TestApp(app)
    msg = {'query':''} # a dict representing the message object expected by insert
#             # To be serialised to JSON by webtest
    resp = testapp.post_json('/_ah/spi/CatalogApi.search', msg)
#    resp = testapp.get('/_ah/spi/uvalibrary/v0.1/catalog/search')
    self.assertEqual(resp.json, {'expected': 'json response msg as dict'})

#if __name__ == '__main__':
#    unittest.main()


#
#
#from google.appengine.ext import testbed
#import webtest
## ...
#def setUp(self):
#    tb = testbed.Testbed()
#    tb.setup_env(current_version_id='testbed.version') #needed because endpoints expects a . in this value
#    tb.activate()
#    tb.init_all_stubs()
#    self.testbed = tb
#
#def tearDown(self):
#    self.testbed.deactivate()
#
#def test_endpoint_insert(self):
#    app = endpoints.api_server([TestEndpoint], restricted=False)
#    testapp = webtest.TestApp(app)
#    msg = {...} # a dict representing the message object expected by insert
#                # To be serialised to JSON by webtest
#    resp = testapp.post_json('/_ah/spi/TestEndpoint.insert', msg)
#
#    self.assertEqual(resp.json, {'expected': 'json response msg as dict'})