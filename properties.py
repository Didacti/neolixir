from decimal import Decimal
from datetime import datetime

__all__ = ['Boolean', 'String', 'Integer', 'Float', 'Numeric', 'DateTime', 'Array', 'RelOut', 'RelIn']

class PropertyContainer(dict):

    def __init__(self, owner, data=None):
        super(PropertyContainer, self).__init__()
        self.owner = owner
        self.reload(data)

    def reset_class(self):
        super(PropertyContainer, self).__setitem__('__class__', self.owner.__class__.__name__)

    def is_dirty(self):
        return self._dirty

    def set_dirty(self, dirty=True):
        self._dirty = dirty

    def reload(self, data=None):
        super(PropertyContainer, self).clear()
        if data is None and self.owner._entity is not None:
            data = self.owner._entity.get_properties()
        if isinstance(data, dict):
            super(PropertyContainer, self).update(data)
        self.set_dirty(False)

    def save(self):
        self.reset_class()
        self.owner._entity.set_properties(self)
        self.set_dirty(False)

    def __setitem__(self, key, value):
        if self.get(key) != value:
            self.set_dirty()
        super(PropertyContainer, self).__setitem__(key, value)

    def __delitem__(self, key):
        self.set_dirty()
        super(PropertyContainer, self).__delitem__(key)

    def clear(self):
        self.set_dirty()
        super(PropertyContainer, self).clear()

    def pop(self, key, default=None):
        self.set_dirty()
        return super(PropertyContainer, self).pop(key, default)

    def popitem(self):
        self.set_dirty()
        return super(PropertyContainer, self).popitem()

    def setdefault(self, key, default=None):
        self.set_dirty()
        return super(PropertyContainer, self).setdefault(key, default)

    def update(self, *args, **kwargs):
        self.set_dirty()
        return super(PropertyContainer, self).update(*args, **kwargs)

class Property(object):

    def __init__(self, name=None):
        self._name = None
        self.name = name

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        if self._name is None:
            self._name = name

class FieldProperty(Property):

    _type = None

    def __init__(self, name=None, default=None):
        super(FieldProperty, self).__init__(name)
        self.default = default

    def __get__(self, instance, owner):
        if instance is None:
            return self
        else:
            value = instance.properties.get(self.name)
            return self.normalize(value if value is not None else self.default)
    
    def __set__(self, instance, value):
        instance.properties[self.name] = self.normalize(value)
    
    def __delete__(self, instance):
        del instance.properties[self.name]

    def normalize(self, value):
        if value is not None and self._type is not None:
            if not isinstance(value, self._type):
                value = self._type(value)
        return value

class Boolean(FieldProperty):

    _type = bool

class String(FieldProperty):

    _type = unicode

class Integer(FieldProperty):

    _type = int

class Float(FieldProperty):

    _type = float

class Numeric(FieldProperty):

    _type = Decimal

    def __init__(self, scale=None, name=None, default=None):
        super(Numeric, self).__init__(name=name, default=default)
        self.scale = scale
    
    def __set__(self, instance, value):
        if value is not None:
            value = str(value)
        instance.properties[self.name] = value

    def normalize(self, value):
        value = super(Numeric, self).normalize(value)
        if self.scale is not None and isinstance(value, Decimal):
            value = value.quantize(Decimal('1.' + '0' * self.scale))
        return value

class DateTime(FieldProperty):

    _type = datetime

    def __get__(self, instance, owner):
        if instance is None:
            return self
        else:
            value = instance.properties.get(self.name)
            if value is not None and not isinstance(value, datetime):
                try:
                    value = datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    value = None
            return value if value is not None else self.default
    
    def __set__(self, instance, value):
        if value is not None:
            value = value.strftime("%Y-%m-%d %H:%M:%S")
        instance.properties[self.name] = value

class Array(FieldProperty):

    def __init__(self, type=None, name=None):
        super(Array, self).__init__(name=name)
        self._type = type

    def __get__(self, instance, owner):
        value = super(Array, self).__get__(instance, owner)
        if instance is not None and not isinstance(value, TypedList):
            value = TypedList(value, type=self._type)
            super(Array, self).__set__(instance, value)
        return value

    def __set__(self, instance, value):
        if not isinstance(value, TypedList):
            value = TypedList(value, type=self._type)
        super(Array, self).__set__(instance, value)

class TypedList(list):
    
    # TODO: implement type checking, casting and enforcing

    def __init__(self, list=None, type=None):
        super(TypedList, self).__init__(list or [])
        self._type = type

class RelProperty(Property):

    direction = None

    def __init__(self, type, name=None):
        super(RelProperty, self).__init__(name)
        self.type = type

    def __get__(self, instance, owner):
        if instance is None:
            return self
        else:
            try:
                return instance._relfilters[self.name]
            except KeyError:
                from relationship import RelationshipFilter
                instance._relfilters[self.name] = RelationshipFilter(instance, self.direction, self.type)
                if len(instance._relfilters) == 1:
                    instance._relfilters[self.name].reload()
                return instance._relfilters[self.name]

class RelOut(RelProperty):

    direction = 'OUT'

class RelIn(RelProperty):

    direction = 'IN'
