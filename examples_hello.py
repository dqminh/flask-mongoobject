from flask import Flask
from flaskext.mongoobject import MongoObject

app = Flask(__name__)
app.config['MONGODB_HOST'] = "mongodb://localhost:27017"
app.config['DEBUG'] = True
app.config['MONGODB_DATABASE'] = "hello"

db = MongoObject(app)

class Post(db.Model):
    __collection__ = "posts"

@app.route("/")
def index():
    post = Post(name="test", author="Daniel")
    post.save()

    post = Post.query.find_one({"name": "test"})
    total = Post.query.count()
    return "Total: %d. Post name: %s by author: %s" % (total, post.name,
                                                       post.author)

if __name__ == "__main__":
    app.run()
