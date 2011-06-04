from attest import Tests, assert_hook
import flask
from flaskext.attest import request_context
from flaskext.mongoobject import AttrDict, MongoObject


db = MongoObject()
app = flask.Flask(__name__)
TESTING = True


class TestModel(db.Model):
    __collection__ = "tests"


db.set_mapper(TestModel)


@request_context
def setup_app():
    app.config['MONGODB_HOST'] = "mongodb://localhost:27017"
    app.config['MONGODB_DATABASE'] = "testdb"
    app.config['MONGODB_AUTOREF'] = True
    app.config['TESTING'] = True
    yield app


mongounit = Tests()
mongointegration = Tests(contexts=[setup_app])


@mongointegration.context
def init_db():
    db.init_app(app)
    try:
        yield
    finally:
        db.clear()


@mongounit.test
def convert_dict_to_object():
    test = AttrDict({"a": "b"})
    assert test.a == "b"


@mongounit.test
def convert_nested_dict_to_object():
    test = AttrDict({"a": {"b": "c"}})
    assert test.a.b == "c"

@mongounit.test
def convert_list_with_nested_dict():
    test = AttrDict(a=[{"b": {"c": "d"}}])
    assert test.a[0].b.c == "d"


@mongointegration.test
def setup_database_properly(client):
    assert db.app
    assert db.connection
    assert db.session.name == "testdb"


@mongointegration.test
def should_find_a_model(client):
    id = db.session.tests.insert({"test": "hello world"})
    result = TestModel.query.find_one(id)
    assert result.test == "hello world"


@mongointegration.test
def should_be_able_to_find_one_with_query(client):
    id = db.session.tests.insert({"test": "hello world"})
    result = TestModel.query.find_one({"test": "hello world"})
    assert result._id == id
    assert result.test == "hello world"

@mongointegration.test
def should_be_able_to_query_with_find(client):
    db.session.tests.insert({"test": "hello world"})
    db.session.tests.insert({"test": "testing"})
    db.session.tests.insert({"test": "testing", "hello": "world"})
    result = TestModel.query.find({"test": "testing"})
    assert result.count() == 2

@mongointegration.test
def save_should_return_a_class(client):
    test = TestModel({"test": "hello"})
    test.save()
    assert test.test == "hello"

@mongointegration.test
def should_not_override_default_variables(client):
    try:
        TestModel({"query_class": "Hello"})
        assert False
    except AssertionError:
        assert True

    try:
        TestModel({"query": "Hello"})
        assert False
    except AssertionError:
        assert True

    try:
        TestModel({"__collection__": "Hello"})
        assert False
    except AssertionError:
        assert True

@mongointegration.test
def should_handle_auto_dbref(client):
    parent = TestModel(test="hello")
    parent.save()
    child = TestModel(test="test", parent=parent)
    child.save()


    child = TestModel.query.find_one({"test": "test"})
    assert child.parent.test == "hello"
    assert child.parent.__class__.__name__ == "TestModel"
    assert type(child.parent) == TestModel


if __name__ == '__main__':
    mongounit.run()
    mongointegration.run()
