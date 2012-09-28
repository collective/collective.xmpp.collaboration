from zope.component import adapts
from zope.interface import Interface
from collective.solr.flare import PloneFlare
from collective.solr.interfaces import ISolrFlare

class RequestlessPloneFlare(PloneFlare):
    """ The default PloneFlare requires an HTTPRequest object for adaptation.
        We however don't have a request obj when querying from a Twisted component.
    """
    adapts(ISolrFlare, Interface)

