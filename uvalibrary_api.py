import urllib, urllib2, json, hashlib, logging

import endpoints
from protorpc import messages
from protorpc import message_types
from protorpc import remote
from protorpc import protojson

from google.appengine.api import memcache
from google.appengine.ext import deferred


package = 'UVALibrary'

api_version = 'v0.1'
catalogURL = "http://search.lib.virginia.edu/catalog.json"
an_api = endpoints.api(name="uvalibrary", version=api_version)

class Image(messages.Message):
  """Image from the digital repo"""
  id = messages.StringField(1, required=True)

class Item(messages.Message):
  """Item from the catalog."""
  id = messages.StringField(1, required=True)
  title = messages.StringField(2, repeated=True)
  subtitle = messages.StringField(3, repeated=True)
  format = messages.StringField(4, repeated=True)
  library = messages.StringField(5, repeated=True)
  barcode = messages.StringField(6, repeated=True)
  oclc = messages.StringField(7, repeated=True)
  author = messages.StringField(8, repeated=True)
  isbn = messages.StringField(9, repeated=True)
  published_date = messages.StringField(10, repeated=True)
  supplemental_url = messages.StringField(11, repeated=True)
  call_number = messages.StringField(12, repeated=True)
  publisher = messages.StringField(13, repeated=True)
  location = messages.StringField(14, repeated=True)
  source = messages.StringField(15, repeated=True)
  date_indexed = messages.StringField(16, repeated=True)
  url = messages.StringField(17, repeated=True)
  series_title = messages.StringField(18, repeated=True)
  medium = messages.StringField(19, repeated=True)
  upc = messages.StringField(20, repeated=True)
  score = messages.FloatField(21)

class ItemCollection(messages.Message):
  """Collection of Items."""
  count = messages.IntegerField(1, default=0)
  items = messages.MessageField(Item, 2, repeated=True)

STORED_GREETINGS = ItemCollection(items=[
    Item(id='hello world!'),
    Item(id='goodbye world!'),
])


@an_api.api_class(
  resource_name='catalog',
  path='catalog'
)
class CatalogApi(remote.Service):

  def load_result(self, result):
    return Item(
      id=result['id'], 
      title=result.get('title_display',[]),
      subtitle=result.get('subtitle_display',[]),
      format=result.get('format_facet',[]),
      library=result.get('library_facet',[]),
      barcode=result.get('barcode_facet',[]),
      oclc=result.get('oclc_display',[]),
      author=result.get('author_display',[]),
      isbn=result.get('isbn_display',[]),
      published_date=result.get('published_date_display',[]),
      supplemental_url=result.get('url_supp_display',[]),
      call_number=result.get('call_number_display',[]),
      publisher=result.get('published_display',[]),
      location=result.get('location2_facet',[]),
      source=result.get('source_facet',[]),
      date_indexed=result.get('date_first_indexed_facet',[]),
      url=result.get('url_display',[]),
      series_title=result.get('series_title_facet',[]),
      medium=result.get('medium_display',[]),
      upc=result.get('upc_display',[]),
      score=result.get('score',0.0)
    )

  def load_results(self, results):
    collection = ItemCollection()
    collection.count = int(results['response']['numFound'])
    for item in results['response']['docs']:
      collection.items.append( self.load_result(item) )
    return collection

  def cache_collection(self, collection):
    coll = protojson.decode_message(ItemCollection, collection)
    key_vals = dict( (x.id, x) for x in coll.items )
    memcache.set_multi(key_vals, key_prefix="items_")

  SEARCH_RESOURCE = endpoints.ResourceContainer(
    message_types.VoidMessage,
    query=messages.StringField(1, default=''),
    per_page=messages.IntegerField(2, default=10),
    page=messages.IntegerField(3, default=0),
    facets=messages.StringField(4)
  )
  @endpoints.method(SEARCH_RESOURCE, ItemCollection,
                    path='search', 
                    http_method='GET',
                    name='search'
  )
  def search(self, request):
    """ Queries the Library's catalog and digital collections """
    try:
      params = [
        ('q',request.query),
        ('per_page',request.per_page),
        ('page',request.page)
      ]
      if request.facets:
        facets = json.loads(request.facets)
        for facet in facets:
          params.append( ('f['+facet+'_facet][]',facets[facet]) )
      url = catalogURL + '?' + urllib.urlencode(params)
      urlkey = hashlib.sha1(url).hexdigest()
      results = memcache.get(urlkey)
      if results is None:
        results = json.loads( urllib2.urlopen(url).read() )
        deferred.defer( memcache.set, urlkey, results )
      else:
        logging.info('Hit cache for catalog search request!')
      collection = self.load_results(results)
      deferred.defer( self.cache_collection, protojson.encode_message(collection) )
      return collection
    except:
      raise endpoints.InternalServerErrorException('Something went wrong with this catalog request!')

  ID_RESOURCE = endpoints.ResourceContainer(
      message_types.VoidMessage,
      id=messages.StringField(1))
  @endpoints.method(ID_RESOURCE, Item,
                    path='item/{id}', http_method='GET',
                    name='get')
  def get(self, request):
    """ Gets an item from the catalog """
    try:
      return STORED_GREETINGS.items[request.id]
    except (IndexError, TypeError):
      raise endpoints.NotFoundException('Greeting %s not found.' %
                                        (request.id,))

@an_api.api_class(
  resource_name="repository",
  path='repository'
)
class RepositoryAPI(remote.Service):

  IMAGE_RESOURCE = endpoints.ResourceContainer(
    message_types.VoidMessage,
    id=messages.StringField(1),
    region=messages.StringField(2)
  )
  @endpoints.method(IMAGE_RESOURCE, Image,
                    path='image/{id}', http_method='GET',
                    name='get_image')
  def get(self, request):
    """ Gets an image from the digital repo """
    try:
      return None
    except:
      raise endpoints.InternalServerErrorException('Something went wrong with this image request')

@an_api.api_class(
  resource_name='directory',
  path='directory'
)
class DirectoryAPI(remote.Service):

  @endpoints.method(message_types.VoidMessage, ItemCollection,
                    path='search', 
                    http_method='GET',
                    name='search'
  )
  def search(self, unused_request):
    """ Queries the Library's directory """
    return STORED_GREETINGS

  @endpoints.method(message_types.VoidMessage, ItemCollection,
                    path='list', 
                    http_method='GET',
                    name='list'
  )
  def list(self, unused_request):
    """ Lists the entries in the Library's directory """
    return STORED_GREETINGS

  ID_RESOURCE = endpoints.ResourceContainer(
      message_types.VoidMessage,
      id=messages.StringField(1))
  @endpoints.method(ID_RESOURCE, Item,
                    path='entry/{id}', 
                    http_method='GET',
                    name='get')
  def get(self, request):
    """ Gets an entry from the directory """
    try:
      return STORED_GREETINGS.items[request.id]
    except (IndexError, TypeError):
      raise endpoints.NotFoundException('Greeting %s not found.' %
                                        (request.id,))

@an_api.api_class(
  resource_name='hours',
  path='hours'
)
class HoursAPI(remote.Service):

  @endpoints.method(message_types.VoidMessage, ItemCollection,
                    path='list', 
                    http_method='GET',
                    name='list'
  )
  def list(self, unused_request):
    """ List the Library's hours of opperation """
    return STORED_GREETINGS

@an_api.api_class(
  resource_name='jobs',
  path='jobs'
)
class JobsAPI(remote.Service):

  @endpoints.method(message_types.VoidMessage, ItemCollection,
                    path='list', 
                    http_method='GET',
                    name='list'
  )
  def list(self, unused_request):
    """ List the Library's available positions """
    return STORED_GREETINGS

APPLICATION = endpoints.api_server([an_api])