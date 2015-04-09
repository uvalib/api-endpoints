import unittest, webtest, endpoints
import uvalibrary_api
from google.appengine.api import memcache
from google.appengine.ext import ndb
from google.appengine.ext import testbed
from google.appengine.datastore import datastore_stub_util

class TestCases(unittest.TestCase):

  def setUp(self):
    tb = testbed.Testbed()
    tb.setup_env(current_version_id='testbed.version') #needed because endpoints expects a . in this value
    tb.activate()
    tb.init_all_stubs()
    self.testbed = tb

  def tearDown(self):
    self.testbed.deactivate()

  def testCatalog(self):
    app = endpoints.api_server([uvalibrary_api.CatalogApi], restricted=False)
    testapp = webtest.TestApp(app)

    # Empty catalog search query (everything)
    msg = {'query':''}
    resp = testapp.post_json('/_ah/spi/CatalogApi.search', msg)
    # Make sure we have some results
    self.assertIsNotNone( resp.json.get('count', None) )
    self.assertTrue( resp.json['count'] > 0 )

  def testDirections(self):
    app = endpoints.api_server([uvalibrary_api.Directions], restricted=False)
    testapp = webtest.TestApp(app)

    # Empty direction list query
    msg = {}
    resp = testapp.post_json('/_ah/spi/Directions.list', msg)
    # Make sure we have some results
    self.assertTrue( len(resp.json.get('directions',[])) > 0 )