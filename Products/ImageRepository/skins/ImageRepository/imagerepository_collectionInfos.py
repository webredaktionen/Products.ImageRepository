## Script (Python) "kupuInfoForBrains"
##title=Provide dictionaries with information about a list of catalog brains
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=values=None
from Products.CMFCore.utils import getToolByName
import AccessControl
from AccessControl import Unauthorized

request = context.REQUEST
response = request.RESPONSE
imagerepository = context.restrictedTraverse('@@image_repository_view')
request_keywords = request.get('keywords',[])
if values is None:
    values = imagerepository.queryImageRepository()
    keywords = imagerepository.getSearchKeywordsFromResults(values)
    if not keywords and not request_keywords:
        # When there are only keywords used on all images in the repository
        # return these instead. This is always the case when there is only 1
        # image, for example.
        keywords = imagerepository.getUniqueKeywordsFromResults(values)
    return_values = len(request_keywords) > 0
else:
    keywords = []
    return_values = True
response.setHeader('Cache-Control', 'no-cache')

makeImageRepositoryQuery = imagerepository.makeImageRepositoryQuery
image_repository_url = "%s/imagerepository_collection.xml" % imagerepository.getImageRepositoryURL()

types_tool = getToolByName(context, 'portal_types')
kupu_tool = getToolByName(context, 'kupu_library_tool')
url_tool = getToolByName(context, 'portal_url')
uid_catalog = getToolByName(context, 'uid_catalog', None)

linkbyuid = kupu_tool.getLinkbyuid()
coll_types = kupu_tool.queryPortalTypesForResourceType('collection', ())
portal_base = url_tool.getPortalPath()
prefix_length = len(portal_base)+1

# The redirecting url must be absolute otherwise it won't work for
# preview when the page is using portal_factory
# The absolute to relative conversion when the document is saved
# should strip the url right back down to resolveuid/whatever.
base = context.absolute_url()
security = AccessControl.getSecurityManager()

image_sizes_cache = {}

def get_image_sizes(obj, portal_type, url):
    if not image_sizes_cache.has_key(portal_type):
        if getattr(obj, 'getObject', None) is not None:
            obj = obj.getObject()
        if getattr(obj, 'getField', None) is None:
            return
        image_field = obj.getWrappedField('image')
        if image_field is None:
            return
        if getattr(image_field, 'getAvailableSizes', None) is None:
            return
        image_sizes_cache[portal_type] = image_field.getAvailableSizes(obj)
    image_sizes = image_sizes_cache[portal_type]
    results = []
    sizes = [((v[0], v[1]), k) for k,v in image_sizes.items()]
    sizes.sort()
    for size, key in sizes:
        info = {'label':"%s (%sx%s)" % (key.capitalize(), size[0], size[1]),
                'uri':"%s/image_%s" % (url, key)}
        if key == 'mini':
            info['selected'] = True
        results.append(info)
    return results

def info_object(obj, allowCollection=True):
    '''Get information from a content object'''

    # Parent folder might not be accessible if we came here from a
    # search.
    if not security.checkPermission('View', obj):
        return None

    try:
        id = obj.getId()
        portal_type = getattr(obj, 'portal_type','')
        collection = allowCollection and portal_type in coll_types

        if hasattr(obj.aq_explicit, 'UID'):
            uid = obj.UID()
        else:
            uid = id

        # Plone issue #4769: this should use
        # IReferenceable.implements(), only that isn't exposed to
        # scripts.
        if linkbyuid and not collection and hasattr(obj.aq_explicit, 'UID'):
            url = base+'/resolveuid/%s' % uid
        else:
            url = obj.absolute_url()

        icon = "%s/%s" % (context.portal_url(), obj.getIcon(1))
        width = height = size = None
        preview = kupu_tool.getPreviewUrl(portal_type, url)

        sizes = get_image_sizes(obj, portal_type, url)

        try:
                size = context.getObjSize(obj)
        except:
            size = None

        ## if showimagesize:
            ## width = getattr(obj, 'width', None)
            ## height = getattr(obj, 'height', None)
            ## if callable(width): width = width()
            ## if callable(height): height = height()

        title = obj.Title() or obj.getId()
        description = obj.Description()

        return {'id': id, 'url': url, 'portal_type': portal_type,
              'collection':  collection, 'icon': icon, 'size': size,
              'width': width, 'height': height, 'sizes': sizes,
              'preview': preview, 'title': title, 'description': description,
              'uid': uid,
              }
    except Unauthorized:
        return None

def info(brain, allowCollection=True):
    '''Get information from a brain'''
    id = brain.getId

    url = brain.getURL()
    portal_type = brain.portal_type
    collection = portal_type in coll_types

    # Path for the uid catalog doesn't have the leading '/'
    path = brain.getPath()
    UID = None
    if path and uid_catalog:
        try:
            metadata = uid_catalog.getMetadataForUID(path[prefix_length:])
        except KeyError:
            metadata = None
        if metadata:
            UID = metadata.get('UID', None)

    if UID is not None:
        uid = UID
    else:
        uid = id

    if linkbyuid and not collection and UID is not None:
        url = base+'/resolveuid/%s' % UID
    else:
        url = brain.getURL()

    if portal_type in ('Image',):
        icon = "%s/image_listing" % url
    else:
        icon = "%s/%s" % (context.portal_url(), brain.getIcon)
    width = height = size = None
    preview = "image_thumb"

    sizes = get_image_sizes(brain, portal_type, url)

    # It would be nice to do everything from the brain, but
    # unfortunately we need to get the object for the preview size.
    # XXX Figure out some way to get the image size client side
    # instead of inserting it here.
    ## if showimagesize:
        ## obj = brain.getObject()
        ## if hasattr(obj, 'get_size'):
            ## size = context.getObjSize(obj)
        ## width = getattr(obj, 'width', None)
        ## height = getattr(obj, 'height', None)
        ## if callable(width): width = width()
        ## if callable(height): height = height()
        
    title = brain.Title or brain.getId
    description = brain.Description

    return {'id': id, 'url': url, 'portal_type': portal_type,
          'collection':  collection, 'icon': icon, 'size': size,
          'width': width, 'height': height, 'sizes': sizes,
          'preview': preview, 'title': title, 'description': description,
          'uid': uid,
          }

def info_keyword(keyword, allowCollection=True):
    id = keyword

    url = "%s?%s" % (image_repository_url, makeImageRepositoryQuery(data=request.form, add={'keywords':[keyword]}))
    portal_type = None
    collection = True

    icon = "%s/%s" % (context.portal_url(), 'folder_icon.gif')
    width = height = size = None
    preview = None

    if getattr(keywords, 'getValue', None) is not None:
        title = keywords.getValue(keyword)
    else:
        title = keyword
    description = ""

    return {'id': id, 'url': url, 'portal_type': portal_type,
          'collection':  collection, 'icon': icon, 'size': size,
          'width': width, 'height': height,
          'preview': preview, 'title': title, 'description': description,
          'uid': id,
          }

# For Plone 2.0.5 compatability, if getId is callable we assume
# we have an object rather than a brains.
if values and callable(values[0].getId):
    info = info_object

# return [info(brain) for brain in values]
res = []

## portal = url_tool.getPortalObject()
## if linkhere and portal is not context:
    ## data = info_object(context, False)
    ## if data:
        ## data['label'] = '. (%s)' % context.title_or_id()
        ## res.append(data)

## if linkparent:
    ## if portal is not context:
        ## data = info_object(context.aq_parent, True)
        ## if data:
            ## data['label'] = '.. (Parent folder)'
            ## res.append(data)

# this doesn't work as expected
if return_values:
    data = info_keyword('..', True)
    if data is not None and len(request_keywords) > 0:
        data['label'] = '.. (Parent folder)'
        data['url'] = "%s?%s" % (image_repository_url, makeImageRepositoryQuery(data=request.form, omit={'keywords':[request_keywords[-1]]}))
        res.append(data)

for keyword in keywords:
    data = info_keyword(keyword, True)
    if data:
        res.append(data)

if return_values:
    for obj in values:
        data = info(obj, True)
        if data:
            res.append(data)
elif values:
    # Top level, show images without keywords
    for obj in values:
        if obj.Subject:
            continue
        data = info(obj, True)
        if data:
            res.append(data)

return res
