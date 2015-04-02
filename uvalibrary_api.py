import urllib, urllib2, json, hashlib, logging, time, re
import xml.etree.ElementTree as ET

import endpoints
from protorpc import messages
from protorpc import message_types
from protorpc import remote
from protorpc import protojson

from google.appengine.api import memcache
from google.appengine.ext import deferred
from google.appengine.api import urlfetch

package = 'UVALibrary'

api_version = 'v0.1'
catalogURL = "http://search.lib.virginia.edu/catalog.json"
directionsURL = "https://spreadsheets.google.com/feeds/list/1FTA9scrRR17pmeRZNPOXZAYhgeG-40FcJp6Ry5_O7Gw/1/public/full?alt=json"
an_api = endpoints.api(name="uvalibrary", version=api_version)

class Image(messages.Message):
  """Image from the digital repo"""
  id = messages.StringField(1, required=True)

class Copy(messages.Message):
  copy_number = messages.StringField(1)
  current_periodical = messages.BooleanField(2)
  barcode = messages.StringField(3)
  shadowed = messages.BooleanField(4, default=False)
  circulate = messages.BooleanField(5, default=True)
  current_location = messages.StringField(6)
  current_location_code = messages.StringField(7)
  home_location = messages.StringField(8)
  home_location_code = messages.StringField(9)
  item_type_code = messages.StringField(10)
  last_checkout = messages.StringField(11)

class Holding(messages.Message):
  call_number = messages.StringField(1)
  call_number_normalized = messages.StringField(2)
  call_sequence = messages.StringField(3)
  can_hold = messages.BooleanField(4, default=True)
  shadowed = messages.BooleanField(5, default=False)
  copies = messages.MessageField(Copy, 6, repeated=True)
  library = messages.StringField(7)
  library_code = messages.StringField(8)
  deliverable = messages.BooleanField(9, default=False)
  holdable = messages.BooleanField(10, default=False)
  remote = messages.BooleanField(11, default=False)

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
  can_hold = messages.BooleanField(22, default=True)
  can_hold_message = messages.StringField(23)
  holdings = messages.MessageField(Holding, 24, repeated=True)

class ItemCollection(messages.Message):
  """Collection of Items."""
  count = messages.IntegerField(1, default=0)
  items = messages.MessageField(Item, 2, repeated=True)

class Direction(messages.Message):
  library = messages.StringField(1)
  title = messages.StringField(2)
  location_key = messages.StringField(3)
  format_key = messages.StringField(4)
  call_key = messages.StringField(5)
  start_call_number = messages.StringField(6)
  end_call_number = messages.StringField(7)
  floor = messages.StringField(8)
  area = messages.StringField(9)
  direction = messages.StringField(10)

class DirectionCollection(messages.Message):
  """Collection of Directions."""
  directions = messages.MessageField(Direction, 1, repeated=True)

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

  def load_holdings(self, holdings_result, item):
    root = ET.fromstring(holdings_result.content)
    can_hold = root.find('canHold')
    if can_hold:
      item.can_hold = can_hold.attrib.get('value',"yes") != "no"
      item.can_hold_message = can_hold.find('message').text
    holdings = root.findall('holding')
    if len(holdings) > 0:
      item.holdings = []
      for holding_info in holdings:
        holding = Holding()
        holding.call_number = holding_info.attrib.get('callNumber','')
        holding.call_number_normalized = holding_info.find('shelvingKey').text
        holding.call_sequence = holding_info.attrib.get('callSequence','')
        holding.can_hold = holding_info.attrib.get('holdable','true') != "false"
        holding.shadowed = holding_info.attrib.get('shadowed','true') != "false"
        holding.copies = []
        for copy_info in holding_info.findall('copy'):
          copy = Copy()
          copy.copy_number = copy_info.attrib.get('copyNumber','')
          copy.current_periodical = copy_info.attrib.get('currentPeriodical','true') != "false"
          copy.barcode = copy_info.attrib.get('barcode','')
          copy.shadowed = copy_info.attrib.get('shadowed','true') != "false"
          copy.circulate = copy_info.find('circulate') == "Y"
          current_loc = copy_info.find('currentLocation')
          copy.current_location = current_loc.find('name').text
          copy.current_location_code = current_loc.attrib.get('code','')
          home_loc = copy_info.find('homeLocation')
          copy.home_location = home_loc.find('name').text
          copy.home_location_code = home_loc.attrib.get('code','')
          copy.item_type_code = copy_info.find('itemType').attrib.get('code','')
          copy.last_checkout = copy_info.find('lastCheckout').text
          holding.copies.append(copy)
        library_info = holding_info.find('library')
        holding.library = library_info.find('name').text
        holding.library_code = library_info.attrib.get('code','')
        holding.deliverable = library_info.find('deliverable').text != "false"
        holding.holdable = library_info.find('holdable').text != "false"
        holding.remote = library_info.find('remote').text != "false"
        item.holdings.append(holding)

  "do this ascyn so we don't have to wait"
  def get_collection_availability(self, collection):
    # For each item, get the availability
    def handle_result(rpc, item):
      logging.info(item.title)
      result = rpc.get_result()
      self.load_holdings(result, item)

    # Use a helper function to define the scope of the callback.
    def create_callback(rpc, item):
      return lambda: handle_result(rpc, item)

    rpcs = []
    for item in collection.items:
      if re.match(r'u\d+$', item.id) is not None:
        url = "http://search.lib.virginia.edu/catalog/"+item.id+"/firehose"
        logging.info(url)
        rpc = urlfetch.create_rpc()
        rpc.callback = create_callback(rpc, item)
        urlfetch.make_fetch_call(rpc, url)
        rpcs.append(rpc)

    # Finish all RPCs, and let callbacks process the results.
    for rpc in rpcs:
      rpc.wait()

  def load_results(self, results):
    collection = ItemCollection()
    collection.count = int(results['response']['numFound'])
    for item in results['response']['docs']:
      collection.items.append( self.load_result(item) )
    return collection

  def cache_collection(self, collection):
    coll = protojson.decode_message(ItemCollection, collection)
    key_vals = dict( (x.id, protojson.encode_message(x)) for x in coll.items )
    memcache.set_multi(key_vals, key_prefix="items_")

  def get_cached_item(self, id):
    item = memcache.get("items_"+str(id))
    if item is not None:
      return protojson.decode_message(Item, item)
    else:
      return item

  SEARCH_RESOURCE = endpoints.ResourceContainer(
    message_types.VoidMessage,
    query=messages.StringField(1, default=''),
    per_page=messages.IntegerField(2, default=10),
    page=messages.IntegerField(3, default=0),
    facets=messages.StringField(4),
    availability=messages.BooleanField(5, default=False)
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
        memcache.set(urlkey, results)
      else:
        logging.info('Hit cache for catalog search request!')
      collection = self.load_results(results)
      deferred.defer( self.cache_collection, protojson.encode_message(collection) )
      if request.availability:
        self.get_availability(collection)
      return collection
    except:
      raise endpoints.InternalServerErrorException('Something went wrong with this catalog request!')

  ID_RESOURCE = endpoints.ResourceContainer(
      message_types.VoidMessage,
      id=messages.StringField(1))
  @endpoints.method(ID_RESOURCE, Item,
                    path='get_item/{id}', http_method='GET',
                    name='get_item')
  def get_item(self, request):
    """ Gets an item from the catalog """
    try:
      item = self.get_cached_item(request.id)
      if item is not None:
        return item
      else:
        raise endpoints.NotFoundException('I could not find that Item, Sorry!')
    except:
      raise endpoints.InternalServerErrorException('Something went wrong with this catalog request!')

@an_api.api_class(
  resource_name="directions",
  path="directions"
)
class Directions(remote.Service):
  
  def load_directions(self, results):
    directs = DirectionCollection()
    for entry in results.get('feed',{'entry':[]})['entry']:
      direct = Direction()
      direct.library = 'alderman'
      direct.title = entry['gsx$title']['$t']
      direct.location_key = entry['gsx$lockey']['$t']
      direct.format_key = entry['gsx$formatkey']['$t']
      direct.call_key = entry['gsx$callkey']['$t']
      direct.start_call_number = entry['gsx$start']['$t']
      direct.end_call_number = entry['gsx$end']['$t']
      direct.floor = entry['gsx$floor']['$t']
      direct.area = entry['gsx$area']['$t']
      direct.direction = entry['gsx$direct']['$t']
      directs.directions.append(direct)
    return directs

  @endpoints.method(message_types.VoidMessage, DirectionCollection,
                    path='list', 
                    http_method='GET',
                    name='list'
  )
  def list(self, unused_request):
    """ Listing of all the (documented) directions to physical items in the library """
    directs = memcache.get('item-directions')
    if directs is None:
        results = json.loads( urllib2.urlopen(directionsURL).read() )
        directs = self.load_directions(results)
#        memcache.set('item-directions', directs.encode_message(directs))
        return directs
    else:
        logging.info('Hit cache for directions list request!')
        return protojson.decode_message(DirectionCollection, directs)

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