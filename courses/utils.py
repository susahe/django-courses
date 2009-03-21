import re
import unicodedata
from htmlentitydefs import name2codepoint

from django.core.serializers import serialize
from django.db.models.query import QuerySet
from django.db.models import CharField
from django.http import HttpResponse
from django.utils import simplejson
from django.utils.functional import Promise 
from django.utils.encoding import force_unicode 

try:
    import uuid
except ImportError:
    from django.utils import uuid

### AJAX response utils ###

class LazyEncoder(simplejson.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Promise):
            return force_unicode(obj)
        return obj

class JSONResponse(HttpResponse):
    """
    A simple subclass of ``HttpResponse`` which makes serializing to JSON easy.
    """
    def __init__(self, object, is_iterable = True):
        if is_iterable:
            content = serialize('json', object)
        else:
            content = simplejson.dumps(object, cls=LazyEncoder)
        super(JSONResponse, self).__init__(content, mimetype='application/json')

class XMLResponse(HttpResponse):
    """
    A simple subclass of ``HttpResponse`` which makes serializing to XML easy.
    """
    def __init__(self, object, is_iterable = True):
        if is_iterable:
            content = serialize('xml', object)
        else:
            content = object
        super(XMLResponse, self).__init__(content, mimetype='application/xml')

### UUID custom field ###
# Snippet taken from http://www.djangosnippets.org/snippets/335/ on 12 March 2009

class UUIDVersionError(Exception):
    pass

class UUIDField(CharField):
    """ UUIDField for Django, supports all uuid versions which are natively
        suported by the uuid python module.
    """

    def __init__(self, verbose_name=None, name=None, auto=True, version=1, node=None, clock_seq=None, namespace=None, **kwargs):
        kwargs['max_length'] = 36
        if auto:
            kwargs['blank'] = True
            kwargs['editable'] = kwargs.get('editable', False)
        self.version = version
        if version==1:
            self.node, self.clock_seq = node, clock_seq
        elif version==3 or version==5:
            self.namespace, self.name = namespace, name
        CharField.__init__(self, verbose_name, name, **kwargs)

    def get_internal_type(self):
        return CharField.__name__

    def create_uuid(self):
        if not self.version or self.version==4:
            return uuid.uuid4()
        elif self.version==1:
            return uuid.uuid1(self.node, self.clock_seq)
        elif self.version==2:
            raise UUIDVersionError("UUID version 2 is not supported.")
        elif self.version==3:
            return uuid.uuid3(self.namespace, self.name)
        elif self.version==5:
            return uuid.uuid5(self.namespace, self.name)
        else:
            raise UUIDVersionError("UUID version %s is not valid." % self.version)

    def pre_save(self, model_instance, add):
        if add:
            value = unicode(self.create_uuid())
            setattr(model_instance, self.attname, value)
            return value
        else:
            value = super(UUIDField, self).pre_save(model_instance, add)
            if not value:
                value = unicode(self.create_uuid())
                setattr(model_instance, self.attname, value)
        return value

### unique slug creation ###
# Snippet taken from http://www.djangosnippets.org/snippets/1030/ on 12 March 2009

def slugify(s, entities=False, decimal=False, hexadecimal=False, invalid=None,
        instance=None, manager=None, slug_field='slug', extra_lookup=None):
    """
    Will try to make the best url string out of any string. If the `entities`
    keyword is True it will try to translate html entities. The `decimal`
    keyword is for decimal html character reference, `hexadecimal` for
    hexadecimal.
    `invalid` should be a list or tuple of invalid slugs. You can also pass
    a Django model instance as `instance`, slugify will then make sure it is a
    unique slug for that model. The keyword `extra_lookup` should be a
    dictionary containing extra lookup. Use this to make the slug unique only
    within the the lookup. For example:
    extra_lookup = {'date': datetime.date.today()} slugify will make
    the slug unique for rows where the column 'date' is todays date. `slug_field`
    is the field in the model to match for uniqueness. You can pass a manager
    to use instead of the default one as `manager`.
    """
    s = force_unicode(s)
    if entities:
        s = re.sub('&(%s);' % '|'.join(name2codepoint),
                lambda m: unichr(name2codepoint[m.group(1)]), s)
    if decimal:
        try:
            s = re.sub('&#(\d+);',
                    lambda m: unichr(int(m.group(1))), s)
        except ValueError:
            pass
    if hexadecimal:
        try:
            s = re.sub('&#x([\da-fA-F]+);',
                    lambda m: unichr(int(m.group(1), 16)), s)
        except ValueError:
            pass
    
    #translate
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore')
    #replace unwanted characters
    s = re.sub(r'[^-a-z0-9]+', '-', s.lower())
    #remove redundant -
    s = re.sub('-{2,}', '-', s).strip('-')

    invalid = invalid or []
    if instance:
        lookup = extra_lookup or {}
        if not manager:
            manager = instance.__class__._default_manager
    
    slug, counter = s, 2 #modified to start numbering at -2 not -1 (Ozan, 22/12/08)
    while True:
        if slug in invalid:
            pass
        elif not instance:
            return slug
        else:
            lookup[slug_field] = slug
            qs = manager.filter(**lookup)
            if instance.pk:
                qs = qs.exclude(pk=instance.pk)
            if not qs.count():
                return slug
        slug = "%s-%s" % (s, counter)
        counter += 1
