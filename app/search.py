import os
from operator import attrgetter
import sqlite3 as sql
import logging

# logging config
logging.basicConfig(
	level=logging.DEBUG,
	format="%(asctime)s | %(levelname)s | %(message)s"
)

curdir = os.path.abspath(os.path.dirname(__file__))

# database connection
db = sql.connect(curdir + "/disk.db")
cu = db.cursor()

# === setup === #
class Post():
	def __init__(self, post):
		self.id = post[0]
		self.heading = post[1]
		self.content = post[2]
		self.author = post[3]
		self.date_published = post[4]
	
	def __repr__(self):
		return f"post {self.id}; {self.heading[:15]}..."

class Hit(Post):
	def __init__(self, post):
		super().__init__(post)
		
		self.score = 0

corpus = {}

def update_index(post):
	try:
		post = Post(post)
	except:
		logging.warning(f"couldn't parse object:\n\t {post}")
		return
	
	body = post.heading + '\n' + post.content
	token = [normalize(value) for value in body.split()]
	
	for value in token:
		entry = corpus.get(value, [])
		entry.append(post.id)
		corpus[value] = list(set(entry))

def search(query):
	token = [normalize(value) for value in query.split()]
	
	pool = []
	for value in token:
		hits = corpus.get(value, [])
		pool.extend(hits)
	pool = list(set(pool))
	
	results = rank(pool, query)
	
	return results

def rank(pool, query):
	hits = []
	for post_id in pool:
		post = cu.execute(f"select * from posts where id={post_id};").fetchone()
		hits.append(Hit(post))
	
	for hit in hits:
		body = hit.heading + "\n" + hit.content
		if body.find(query) is not -1:
			hit.score += 3
		
		args = [normalize(arg) for arg in query.split()]
		for arg in args:
			hit.score += arg_freq(arg, body)
	
	hits = sorted(hits, key=attrgetter('score'), reverse=True)
	
	return [hit.id for hit in hits]

def arg_freq(arg, body):
	body = [normalize(word) for word in body.split()]
	
	return body.count(arg)

def normalize(value):
	# to lower case
	value = value.lower()
	# strip leading and trailing spaces
	value = value.strip()
	# strip leading and trailing punctuations
	value = value.strip(".")
	value = value.strip(",")
	value = value.strip("'")
	
	return value


posts = cu.execute("select * from posts;").fetchall()
for post in posts:
	update_index(post)
logging.info("corpus is up to date")
