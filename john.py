# john: keep a journal

import tornado.web
import tornado.ioloop
from tornado import gen

import os
import time
import secrets
import hashlib
import time
import markdown
import sqlite3 as sql
print ("importing dependencies...")

# sql database connection
db = sql.connect("disk.db")
cu = db.cursor()
print ("setting up database...")

# secure token
token = secrets.token_hex(5)

class User():
	def __init__(self, user):
		self.username = user[0]
		self.password = user[1]

class Post():
	# return just the date of a datetime string
	def post_date(self, date_string):
		d_date = date_string.split(";")[0]
		return d_date
	
	# humanize access to post data
	def __init__(self, post):
		self.id = post[0]
		self.heading = post[1]
		self.content = post[2]
		self.html = markdown.markdown(post[2][:150])
		self.author = post[3]
		self.date_published = self.post_date(post[4])

class BaseHandler(tornado.web.RequestHandler):
	def get_current_user(self):
		return self.get_secure_cookie("user")
	
	def user_exists(self, username):
		query = cu.execute(f"""select username from users where username="{username}";""").fetchone()
		return True if query else False
	
	def pswd_authenticated(self, entd_pswd, std_pswd):
		# user exists already
		# confirm that entered password hash matches stored password hash
		
		# bcrypt is to be implemented later on
		entd_pswd = hashlib.md5(entd_pswd.encode()).hexdigest()
		return True if entd_pswd == std_pswd else False
	
	def now(self):
		# time.localtime() returns a tuple of the
		# current time downn ms from years
		
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
		recent_posts = cu.execute("""select * from posts order by date_published desc;""").fetchmany(5)
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
			self.render("auth.html", page=page, error=f"{self.get_argument('username')} is taken")
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
		self.render("auth.html", page=page, error=None)
	
	def post(self):
		page = dict(
			page="login"
			)
		user = cu.execute(f"""select * from users where username="{self.get_argument("username")}";""").fetchone()
		if not user:
			self.render("auth.html", page=page, error="invalid username or password")
			return
		else:
			user = User(user)
			if self.pswd_authenticated(self.get_argument("password"), user.password):
				self.set_secure_cookie("user", self.get_argument("username"))
				self.redirect("/")
			else:
				self.render("auth.html", page=page, error="invalid username or password")

class LogoutHandler(BaseHandler):
	def get(self):
		self.clear_cookie("user")
		self.redirect("/")

class SearchHandler(BaseHandler):
	def get(self):
		page = dict(
			hero="the search"
		)
		self.render("search.html", page=page)
	
	def post(self):
		self.render("search.html", page=page)

class NewPostHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		page = dict(
			action="/posts/new",)
		self.render("editor.html", page=page,)
	
	@tornado.web.authenticated
	def post(self):
		heading = self.get_argument("heading") if self.get_argument("heading") != "" else "heading"
		content = self.get_argument("content") if self.get_argument("content") != "" else "content"
		author = self.current_user.decode()
		pub_date = self.now()
		
		page = dict(
			action="/posts/new",)
		cu.execute(f"""insert into posts("heading", "content", "author", "pub_date") values("{heading}"
		self.redirect("/posts")

class AllPostsHandler(BaseHandler):
	@gen.coroutine
	def get(self):
		page = dict(
			hero="this is all of it"
			)
		posts = cu.execute("""select * from posts order by date_published desc;""").fetchall()
		all = [Post(post) for post in posts]
		
		self.render("posts.html", all=all, page=page)

class PostHandler(BaseHandler):
	def get(self, post_id):
		page = dict(
			hero="the source"
			)
		post = cu.execute(f"""select * from posts where id={post_id};""").fetchone()
		
		# make a post class to ease access
		post = Post(post)
		edit=False
		if self.current_user!=None and self.current_user.decode()==post.author: edit=True
		self.render("post.html", post=post, page=page, edit=edit)



class EditPostHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self, post_id):
		page = dict(
			hero="make your adjustments",
			)
		post = cu.execute(f"""select * from posts where id={post_id};""").fetchone()
		post = Post(post)
		self.render("edit-post.html", post=post, page=page)
	
	@tornado.web.authenticated
	def post(self, post_id):
		heading = self.get_argument("heading")
		content = self.get_argument("content")
		author = self.current_user
		pub_date = self.now()
		
		cu.execute(f"""update posts set heading="{heading}", content="{content}" where id={post_id};""")
		db.commit()
		
		self.redirect(f"/posts/{post_id}")

class DeletePostHandler(BaseHandler):
	def post(self, post_id):
		cu.execute(f"""delete from posts where id={post_id};""")
		db.commit()
		self.redirect("/posts")

class UserPostsHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		page = dict(
			hero="these are yours"
			)
		user=self.current_user.decode()
		all = cu.execute(f"""select * from posts where author="{user}" order by date_published desc;""").fetchall()
		all = [Post(post) for post in all]
		self.render("posts.html", all=all, page=page)

class AboutJohnHandler(BaseHandler):
	def get(self):
		page = dict(
			hero="readme.md"
		)
		self.render("about-john.html", page=page)

class ProfileHandler(BaseHandler):
	def get(self, username):
		page = dict(
			hero=f"this is you, {username}"
		)
		users = cu.execute("""select username from users;""").fetchall()
		if username in users:
			self.render("user-profile.html", page=page, error=None)
			return
		else:
			self.render("user-profile.html", page=page, error="user does not exist")

# ========================== #
app = tornado.web.Application(
	[
		(r"/", HomePage),
		(r"/signup", SignupHandler),
		(r"/login", LoginHandler),
		(r"/logout", LogoutHandler),
		(r"/new-post", NewPostHandler),
		(r"/posts", AllPostsHandler),
		(r"/posts/([0-9]+)", PostHandler),
		(r"/posts/([0-9]+)/edit", EditPostHandler),
		(r"/posts/([0-9]+)/edit/delete", DeletePostHandler),
		(r"/my-posts", UserPostsHandler),
		(r"/about-john", AboutJohnHandler),
		(r"/user/(\w+)", ProfileHandler),
	],
	debug = True,
	cookie_secret = token,
	static_path = os.path.join(os.path.dirname(__file__), "assets"),
	template_path = os.path.join(os.path.dirname(__file__), "pages"),
	login_url = "/login",
	autoescape = None,
)

try:
	print ("starting application...")
	app.listen(8081)
	tornado.ioloop.IOLoop.current().start()
except:
	print ("\nshutting down!")
	import sys; sys.exit()
	