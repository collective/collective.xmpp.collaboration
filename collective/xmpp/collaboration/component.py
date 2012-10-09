import logging
import transaction
import Zope2

from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.SecurityManagement import noSecurityManager
from Products.CMFCore.utils import getToolByName
from plone.registry.interfaces import IRegistry
from twisted.words.protocols.jabber.jid import JID
from zope.app.component.hooks import setSite
from zope.component import getGlobalSiteManager
from zope.component import getUtility
from zope.component import queryUtility

from collective.xmpp.core.utils.users import unescapeNode

from collective.xmpp.core.component import XMPPComponent

from collective.xmpp.collaboration.interfaces import ICollaborativeEditingComponent
from collective.xmpp.collaboration.interfaces import ICollaborativelyEditable
from collective.xmpp.collaboration.interfaces import IProductLayer
from collective.xmpp.collaboration.protocol import DSCException
from collective.xmpp.collaboration.protocol import DifferentialSyncronisationHandler

log= logging.getLogger(__name__)


class CollaborationHandler(DifferentialSyncronisationHandler):
    """ Plone specific component that implements IDifferentialSyncronisation
    """

    def __init__(self, portal):
        super(CollaborationHandler, self).__init__()
        self.portal_id = portal.id

    def userJoined(self, user, node):
        log.info('User %s joined node %s.' % (user, node))

    def userLeft(self, user, node):
        log.info('User %s left node %s.' % (user, node))

    def getNodeText(self, jid, node):
        transaction.begin()
        app = Zope2.app()
        text = ''
        try:
            try:
                portal = app.unrestrictedTraverse(self.portal_id, None)
                if portal is None:
                    raise DSCException(
                        'Portal with id %s not found' % self.portal_id)
                setSite(portal)
                acl_users = getToolByName(portal, 'acl_users')
                user_id = unescapeNode(JID(jid).user)
                user = acl_users.getUserById(user_id)
                if user is None:
                    raise DSCException(
                        'Invalid user %s' % user_id)
                newSecurityManager(None, user)
                ct = getToolByName(portal, 'portal_catalog')
                uid, html_id = node.split('#')
                item = ct.unrestrictedSearchResults(UID=uid)
                if not item:
                    raise DSCException(
                        'Content with UID %s not found' % uid)
                item = ICollaborativelyEditable(item[0].getObject())
                text = item.getNodeTextFromHtmlID(html_id)
                transaction.commit()
            except:
                transaction.abort()
                raise
        finally:
            noSecurityManager()
            setSite(None)
            app._p_jar.close()
        return text

    def setNodeText(self, jid, node, text):
        transaction.begin()
        app = Zope2.app()
        try:
            try:
                portal = app.unrestrictedTraverse(self.portal_id, None)
                if portal is None:
                    raise DSCException(
                        'Portal with id %s not found' % self.portal_id)
                setSite(portal)
                
                settings = getUtility(IRegistry)
                autosave = settings.get('collective.xmpp.autoSaveCollaboration', False)
                if not autosave:
                    transaction.abort()
                    return

                acl_users = getToolByName(portal, 'acl_users')
                user_id = unescapeNode(JID(jid).user)
                user = acl_users.getUserById(user_id)
                if user is None:
                    raise DSCException(
                        'Invalid user %s' % user_id)
                newSecurityManager(None, user)
                ct = getToolByName(portal, 'portal_catalog')
                uid, html_id = node.split('#')
                item = ct.unrestrictedSearchResults(UID=uid)
                if not item:
                    raise DSCException(
                        'Content with UID %s not found' % uid)
                item = ICollaborativelyEditable(item[0].getObject())
                item.setNodeTextFromHtmlID(html_id, text)
                transaction.commit()
            except:
                transaction.abort()
                raise
        finally:
            noSecurityManager()
            setSite(None)
            app._p_jar.close()
        return text


def setupCollaborationComponent(portal, event):
    request = getattr(portal, 'REQUEST', None)
    if not request or not IProductLayer.providedBy(request):
        return

    if queryUtility(ICollaborativeEditingComponent) is None:
        gsm = getGlobalSiteManager()
        registry = getUtility(IRegistry)
        component_jid = registry.get('collective.xmpp.collaborationJID')
        xmpp_domain = registry.get('collective.xmpp.xmppDomain')
        password = registry.get('collective.xmpp.collaborationPassword')
        port = registry.get('collective.xmpp.collaborationPort')
        if component_jid is None or xmpp_domain is None or password is None or port is None:
            log.warn('Could not connect the Collaboration component, check your registry settings')
            return

        component = XMPPComponent(xmpp_domain, port,
            component_jid, password, [CollaborationHandler(portal)])
        gsm.registerUtility(component, ICollaborativeEditingComponent)
