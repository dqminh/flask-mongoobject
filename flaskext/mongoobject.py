# -*- coding: utf-8 -*-
"""
flaskext.mongoobject
~~~~~~~~~~~~~~~~~~~~

Add basic MongoDB support to your Flask application.

Inspiration:
https://github.com/slacy/minimongo/
https://github.com/mitsuhiko/flask-sqlalchemy

:copyright: (c) 2011 by Daniel, Dao Quang Minh (dqminh).
:license: MIT, see LICENSE for more details.
"""
from __future__ import with_statement, absolute_import
from bson.dbref import DBRef
from bson.son import SON
from pymongo import Connection
from pymongo.collection import Collection
from pymongo.cursor import Cursor
from pymongo.son_manipulator import AutoReference, NamespaceInjector

from flask import abort


class AttrDict(dict):
    """
    Base object that represents a MongoDB document. The object will behave both
    like a dict `x['y']` and like an object `x.y`
    """
    def __init__(self, initial=None, **kwargs):
        # Make sure that during initialization, that we recursively apply
        # AttrDict.  Maybe this could be better done with the builtin
        # defaultdict?
        if initial:
            for key, value in initial.iteritems():
                # Can't just say self[k] = v here b/c of recursion.
                self.__setitem__(key, value)
        # Process the other arguments (assume they are also default values).
        # This is the same behavior as the regular dict constructor.
        for key, value in kwargs.iteritems():
            self.__setitem__(key, value)

        super(AttrDict, self).__init__()

    # These lines make this object behave both like a dict (x['y']) and like
    # an object (x.y).  We have to translate from KeyError to AttributeError
    # since model.undefined raises a KeyError and model['undefined'] raises
    # a KeyError.  we don't ever want __getattr__ to raise a KeyError, so we
    # 'translate' them below:
    def __getattr__(self, attr):
        try:
            return super(AttrDict, self).__getitem__(attr)
        except KeyError as excn:
            raise AttributeError(excn)

    def __setattr__(self, attr, value):
        try:
            # Okay to set directly here, because we're not recursing.
            self[attr] = value
        except KeyError as excn:
            raise AttributeError(excn)

    def __delattr__(self, key):
        try:
            return super(AttrDict, self).__delitem__(key)
        except KeyError as excn:
            raise AttributeError(excn)

    def __setitem__(self, key, value):
        new_value = value
        # if the nested attribute is not an :class: `AttrDict` already,
        # convert it to one
        if isinstance(value, dict) and not isinstance(value, AttrDict):
            new_value = AttrDict(value)
        return super(AttrDict, self).__setitem__(key, new_value)


class MongoCursor(Cursor):
    """
    A cursor that will return an instance of :attr:`as_class` instead of
    `dict`
    """
    def __init__(self, *args, **kwargs):
        self.as_class = kwargs.pop('as_class')
        super(MongoCursor, self).__init__(*args, **kwargs)

    def next(self):
        data = super(MongoCursor, self).next()
        return self.as_class(data)

    def __getitem__(self, index):
        item = super(MongoCursor, self).__getitem__(index)
        if isinstance(index, slice):
            return item
        else:
            return self.as_class(item)


class AutoReferenceObject(AutoReference):
    """
    Transparently reference and de-reference already saved embedded objects.

    This manipulator should probably only be used when the NamespaceInjector is
    also being used, otherwise it doesn't make too much sense - documents can
    only be auto-referenced if they have an `_ns` field.

    If the document should be an instance of a :class:`flaskext.mongoobject.Model`
    then we will transform it into a model's instance too.

    NOTE: this will behave poorly if you have a circular reference.

    TODO: this only works for documents that are in the same database. To fix
    this we'll need to add a DatabaseInjector that adds `_db` and then make
    use of the optional `database` support for DBRefs.
    """

    def __init__(self, mongo):
        self.mongo = mongo
        self.db = mongo.session

    def transform_outgoing(self, son, collection):
        def transform_value(value):
            if isinstance(value, DBRef):
                return self.__database.dereference(value)
            elif isinstance(value, list):
                return [transform_value(v) for v in value]
            elif isinstance(value, dict):
                if value.get('_ns', None):
                    # if the collection has a `Model` mapper
                    cls = self.mongo.mapper.get(value['_ns'], None)
                    if cls:
                        return cls(transform_dict(SON(value)))
                return transform_dict(SON(value))
            return value

        def transform_dict(object):
            for (key, value) in object.items():
                object[key] = transform_value(value)
            return object

        value = transform_dict(SON(son))
        return value


class BaseQuery(Collection):
    """
    `BaseQuery` extends :class
    """

    def __init__(self, *args, **kwargs):
        self.document_class = kwargs.pop('document_class')
        super(BaseQuery, self).__init__(*args, **kwargs)

    def find_one(self, *args, **kwargs):
        kwargs['as_class'] = self.document_class
        return super(BaseQuery, self).find_one(*args, **kwargs)

    def find(self, *args, **kwargs):
        kwargs['as_class'] = self.document_class
        return MongoCursor(self, *args, **kwargs)

    def find_and_modify(self, *args, **kwargs):
        kwargs['as_class'] = self.document_class
        return super(BaseQuery, self).find_and_modify(*args, **kwargs)

    def get_or_404(self, id):
        item = self.find_one(id, as_class=self.document_class)
        if not item:
            abort(404)
        return item


class _QueryProperty(object):

    def __init__(self, mongo):
        self.mongo = mongo

    def __get__(self, instance, owner):
        self.mongo.mapper[owner.__collection__] = owner
        return owner.query_class(database=self.mongo.session,
                                 name=owner.__collection__,
                                 document_class=owner)


class Model(AttrDict):
    """Base class for custom user models."""
    #: Query class
    query_class = BaseQuery
    #: instance of :attr:`query_class`
    query = None
    #: name of this model collection
    __collection__ = None

    def __init__(self, *args, **kwargs):
        assert 'query_class' not in kwargs
        assert 'query' not in kwargs
        assert '__collection__' not in kwargs
        super(Model, self).__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        self.query.save(self, *args, **kwargs)
        return self

    def remove(self):
        return self.query.remove(self._id)

    def __str__(self):
        return '%s(%s)' % (self.__class__.__name__,
                           super(Model, self).__str__())

    def __unicode__(self):
        return str(self).decode('utf-8')


class MongoObject(object):
    def __init__(self, app=None):
        if app is not None:
            self.app = app
            self.init_app(app)
        self.Model = self.make_model()

    def init_app(self, app):
        app.config.setdefault('MONGODB_HOST', "mongodb://localhost:27017")
        app.config.setdefault('MONGODB_DATABASE', "")
        app.config.setdefault('MONGODB_AUTOREF', True)
        # initialize connection and Model properties
        self.app = app
        self.mapper = {}
        self.init_connection()

    def init_connection(self):
        self.connection = Connection(self.app.config['MONGODB_HOST'])

    def make_model(self):
        model = Model
        model.query = _QueryProperty(self)
        return model

    @property
    def session(self):
        if not getattr(self, "db", None):
            self.db = self.connection[self.app.config['MONGODB_DATABASE']]
            if self.app.config['MONGODB_AUTOREF']:
                self.db.add_son_manipulator(NamespaceInjector())
                self.db.add_son_manipulator(AutoReferenceObject(self))
        return self.db

    def close_connection(self, response):
        self.connection.end_request()
        return response

    def clear(self):
        self.connection.drop_database(self.app.config['MONGODB_DATABASE'])
        self.connection.end_request()
