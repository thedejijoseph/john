# how does search work?

class Post():
	def __init__(self, post):
		self.id = post[0]
		self.heading = post[1]
		self.content = post[2]

words = {}
index = {}

posts = [
	[1, "hello world", "i am populary reffered to as codde and im here to assert the argument that the world and not the earth is round"],
	[2, "lies", "thats what we scream. you hear that donald skunk! youre a liar"],
	[3, "security", "ive just been employed at my choice company as a security engineer, although its more of a pen testing job. which im in love with as much as heck"],
]

# the question: construct a scalable search engine to query posts
# the solution: crawl and index; process queries; provide relevant results

# check this out: a search for "donald j. trump" returns "post 2" cause of a reference to "donald skunk!"

# use an inverted index to quickly locate the documents containing the words in a query and then rank these documents by relevance

# basic (naively inefficient) search
def basic(query):
	for post in posts:
		post = Post(post)
		if query in post.heading or query in post.content:
			print(f"post {post.id} has {query} in it.\n\tpost heading: {post.heading}\n\tpost content: {post.content}")
		else:
			print(f"{query} was not found in post {post.id}")

