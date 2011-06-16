.. Flask-MongoObject documentation master file, created by
   sphinx-quickstart on Thu Jun 16 12:51:22 2011.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Flask-MongoObject
=================

.. module:: flaskext.mongoobject

Flask-MongoObject is an extension for `Flask`_ that adds support for `MongoDB`_
in your application. It's based on the excellent `pymongo`_ library and add a
few more features such as retrieving objects, auto-refenrence and dereference
objects. The extensions is based on `minimongo`_ but has been adapted to
`Flask`_ and added/removed a few features on its own.


Quickstart: A Sample Application
--------------------------------

For most cases, all you have to do is create your Flask application, loading
your configuration and then create :class:`MongoObject` object by passing the
application to it

Once create, that object will contain all the functions and helpers you need to
access your MongoDB database. It also provides a :class:`Model` that can be
used to declare your Model object::

    from flask import Flask
    from flaskext.mongoobject import MongoObject

    app = Flask(__name__)
    app.config['MONGODB_HOST'] = "mongodb://localhost:27017"
    app.config['DEBUG'] = True
    app.config['MONGODB_DATABASE'] = "hello"

    db = MongoObject(app)

    class Post(db.Model):
        __collection__ = "posts"

Make sure that your MongoDB database is running. To create a new post:

>>> from yourapplication import Post
>>> first = Post(title="test", content="hello")
>>> second = Post({"title": "hello", "content": "second post"})

As you have notice, :class:`Model` can accept both kwargs as well as a
dictionary to populate the model information. The created models have not been
saved into database yet. To save them, simply call:

>>> first.save()
>>> second.save()

Then, when you want to access the saved objects:

>>> User.query.find({"title": "test"})

The :class:`Model` has a `query` attribute similar to `Flask-SQLAlchemy` that
can be used to query the collections. In fact, it's only a very thin layer to
`pymongo.Collection`

Configuration
-------------

A list of configuration keys of the extensions

.. tabularcolumns:: |p{6.5cm}|p{8.5cm}|

=============================== =========================================
``MONGODB_HOST``                accept a full `mongodb uri <http://dochub.mongodb.org/core/connections>`_
                                for the connection.  Examples:
                                "mongodbL//localhost:27017"
``MONGODB_DATABASE``            database that we are going to connect to
=============================== =========================================


.. _Flask: http://flask.pocoo.org
.. _MongoDB: http://mongodb.org
.. _pymongo: http://apy.mongodb.org/python/current
.. _minimongo: http://github.com/slacy/minimongo
.. _example:
    https://github.com/dqminh/flask-mongoobject/blob/master/examples_hello.py
