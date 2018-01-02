# john: keep a journal

import tornado.web
import tornado.ioloop
from tornado import gen

import os
import time
import secrets
import hashlib
import logging
import sqlite3 as sql

import markdown

import search

# sql database connection
db = sql.connect("disk.db")
cu = db.cursor()

# secure token
token = secrets.token_hex(5)

# logging config
logging.basicConfig(
	level = logging.DEBUG,
	format = "%(asctime)s | %(levelnamr)s | %(message)s"
)

logging.info("dependencies imported")
logging.info("setting up application")

# ==== setup ==== #
class User():
	def __init__(self, user):
		self.id = user[0]
		self.username = user[1]
		self.password = user[2]

class Post():
	def __init__(self, post):
		self.id = post[0]
		self.heading = post[1]
		self.content = post[2]
		self.markdown = markdown.markdown(post[2])
		self.brief = self.excerpt()
		self.author = post[3]
		self.date_published = self.post_date(post[4])
	
	def post_date(self, date_string):
		# return just the date of a datetime string
		d_date = date_string.split(";")[0]
		return d_date
	
	def excerpt(self):
		# post excerpt
		content = self.content
		newline = content.find("\n")
		if newline > 145 and newline < 155:
		    brief = content[:newline]
		
		else:
			fullstop = content[150:].find(".")
			brief = content[:fullstop+151]
		
		return markdown.markdown(brief)

class BaseHandler(tornado.web.RequestHandler):
	def get_current_user(self):
		return self.get_secure_cookie("user")
	
	def user_exists(self, username):
		query = cu.execute(f"""select username from users where username="{username}";""").fetchone()
		return True if query else False
	
	def pswd_authenticated(self, entd_pswd, std_pswd):
		# user exists
		# confirm that entered password hash matches stored password hash
		
		# bcrypt to be implemented later on
		entd_pswd = hashlib.md5(entd_pswd.encode()).hexdigest()
		return True if entd_pswd == std_pswd else False
	
	def now(self):
		# time.localtime() returns a tuple of the
		# current time down ms from years
		
		raw = time.localtime()
		months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
		
		Yr, Mo, Dy, Hr, Mn, Sc = raw[:6]
		
		return f"{Dy} {months[Mo-1]}, {Yr}; {Hr}:{Mn}:{Sc}"

# app handlers

# /signup
# /login
# /logout
# /search

# /new-post (auth)
# /posts/id
# /posts
# /posts/id/edit

class HomePage(BaseHandler):
	def get(self):
		recent_posts = cu.execute("""select * from posts order by id desc;""").fetchmany(5)
		recent = [Post(post) for post in recent_posts]
		page = dict()
		
		self.render("index.html", recent=recent, page=page)

class SignupHandler(BaseHandler):
	def get(self):
		page = dict(
			page="signup")
		self.render("auth.html", page=page, error=None)
	
	def post(self):
		page = dict(
			page="signup",)
		
		if self.user_exists(self.get_argument("username")):
			self.render("auth.html", page=page, error=f"username is not available")
		else:
			username = self.get_argument("username")
			password = hashlib.md5(self.get_argument("password").encode()).hexdigest()
			cu.execute(f"""insert into users(username, password) values("{username}", "{password}");""")
		db.commit()
		self.redirect("/login")

class LoginHandler(BaseHandler):
	def get(self):
		page = dict(
			page="login",
			)
		try:
			# redirect to
			rdr_to = self.request.headers["Referer"]
		except:
			rdr_to = "/"
		
		self.render("auth.html", page=page, error=None, next=rdr_to)
	
	def post(self):
		page = dict(
			page="login"
			)
		user = cu.execute(f"""
			select * from users where 
			username="{self.get_argument("username")}";""").fetchone()
		
		if not user:
			self.render("auth.html", page=page, error="invalid username or password")
			return
		else:
			user = User(user)
			if self.pswd_authenticated(self.get_argument("password"), user.password):
				self.set_secure_cookie("user", self.get_argument("username"))
				
				rdr_to = self.get_argument("next")
				self.redirect(rdr_to)
			else:
				self.render("auth.html", page=page, error="invalid username or password")

class LogoutHandler(BaseHandler):
	def get(self):
		self.clear_cookie("user")
		self.redirect("/")

class SearchHandler(BaseHandler):
	def post(self):
		query = self.get_argument("query")
		result = search.search(query)
		if result:
			results = []
			for post_id in result:
				post = cu.execute(f"""select * from posts where id={post_id};""").fetchone()
				results.append(Post(post))
		else:
			results = None
		self.render("results.html", results=results, query=query)

class ProfileHandler(BaseHandler):
	def get(self, username):
		user = cu.execute(f"""select * from users where username="{username}";""").fetchone()
		if user:
			user = User(user)
			posts = cu.execute(f"""select * from posts where author="{user.username}";""").fetchall()
			posts = [Post(post) for post in posts]
			self.render("user.html", user=user, posts=posts, error=None)
			return
		else:
			self.render("user.html", user=None, posts=None, error="user was not found")

class AllPostsHandler(BaseHandler):
	@gen.coroutine
	def get(self):
		page = dict(
			hero="this is all of it"
			)
		posts = cu.execute("""select * from posts order by date_published desc;""").fetchall()
		all = [Post(post) for post in posts]
		
		self.render("posts.html", all=all, page=page)

class NewPostHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		page = dict(
			action="/posts/new",)
		self.render("editor.html", page=page, post=None)
	
	@tornado.web.authenticated
	def post(self):
		heading = self.get_argument("heading") if self.get_argument("heading") != "" else "heading"
		content = self.get_argument("content") if self.get_argument("content") != "" else "content"
		author = self.current_user.decode()
		pub_date = self.now()
		
		page = dict(
			action="/posts/new",)
		
		cu.execute(f"""insert into posts("heading", "content", "author", "date_published") values("{heading}", "{content}", "{author}", "{pub_date}");""")
		db.commit()
		
		# update index
		just_in = cu.execute(f"""select * from posts where id = {cu.lastrowid};""").fetchone()
		search.update_index(just_in)
		
		self.redirect("/posts")

class PostHandler(BaseHandler):
	def get(self, post_id):
		page = dict(
			hero="the source"
			)
		post = cu.execute(f"""select * from posts where id={post_id};""").fetchone()
		
		# make a post object out of it
		post = Post(post)
		self.render("post.html", page=page, post=post)

class EditPostHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self, post_id):
		page = dict(
			action=f"/posts/{post_id}/edit",)
		
		post = cu.execute(f"""select * from posts where id={post_id};""").fetchone()
		if post:
			post = Post(post)
			self.render("editor.html", post=post, page=page)
		else:
			self.redirect("/posts/new")
	
	@tornado.web.authenticated
	def post(self, post_id):
		heading = self.get_argument("heading")
		content = self.get_argument("content")
		author = self.current_user
		pub_date = self.now()
		
		cu.execute(f"""update posts set heading="{heading}", content="{content}" where id={post_id};""")
		db.commit()
		
		# update index
		just_in = cu.execute(f"""select * from posts where id = {cu.lastrowid};""").fetchone()
		search.update_index(just_in)
		
		self.redirect(f"/posts/{post_id}")

class DeletePostHandler(BaseHandler):
	def post(self, post_id):
		cu.execute(f"""delete from posts where id={post_id};""")
		db.commit()
		self.redirect("/posts")

# ========================== #
handlers = [
		(r"/", HomePage),
		(r"/signup", SignupHandler),
		(r"/login", LoginHandler),
		(r"/logout", LogoutHandler),
		(r"/search", SearchHandler),
		(r"/user/(.*)", ProfileHandler),
		(r"/posts", AllPostsHandler),
		(r"/posts/new", NewPostHandler),
		(r"/posts/([0-9]+)", PostHandler),
		(r"/posts/([0-9]+)/edit", EditPostHandler),
		(r"/posts/([0-9]+)/edit/delete", DeletePostHandler),
]

settings = dict(
	debug = True,
	cookie_secret = token,
	static_path = os.path.join(os.path.dirname(__file__), "assets"),
	template_path = os.path.join(os.path.dirname(__file__), "pages"),
	login_url = "/login",
	autoescape = None,
)

app = tornado.web.Application(
	handlers = handlers,
	**settings,
)

logging.info("server up at localhost: 8081")
try:
	app.listen(8081)
	tornado.ioloop.IOLoop.current().start()
except:
	logging.warning("something just went off")
	logging.critical("shutting down!")
	import sys
	sys.exit()
