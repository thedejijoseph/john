# john: keep a journal

import tornado.web
import tornado.ioloop

import os
import time
import secrets
import hashlib
import time
import markdown

# sql database
import sqlite3 as sql

db = sql.connect("disk.db")
cu = db.cursor()

# secure token
token = secrets.token_hex(5)

class User():
	def __init__(self, user):
		# input 'user' is tuple of database columns
		self.username = user[0]
		self.password = user[1]

class Post():
	"""defines the attributes of post,
	user to simplify access"""
	
	# return just the date of a datetime string
	def post_date(self, date_string):
		d_date = date_string.split(";")[0]
		return d_date
	
	def __init__(self, post):
		self.id = post[0]
		self.heading = post[1]
		self.content = post[2]
		self.html = markdown.markdown(post[2])
		self.author = post[3]
		self.date_published = self.post_date(post[4])

class BaseHandler(tornado.web.RequestHandler):
	def get_current_user(self):
		return self.get_secure_cookie("user")
	
	def user_exists(self, username):
		db_query = cu.execute(f"""select username from users where username="{username}";""").fetchone()
		if db_query:
			return True
		else:
			return False
	
	def pswd_authenticated(self, entd_pswd, std_pswd):
		# user exists already
		# confirm that entered password hash matches stored password hash
		
		# bcrypt is to be implemented later on
		entd_pswd = hashlib.md5(entd_pswd.encode()).hexdigest()
		if entd_pswd == std_pswd:
			return True
		else:
			return False
	
	def now(self):
		# time.localtime() returns a tuple of the
		# current time downn ms from years
		
		raw = time.localtime()
		months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
		
		Yr, Mo, Dy, Hr, Mn, Sc = raw[:6]
		
		return f"{Dy} {months[Mo-1]}, {Yr}; {Hr}:{Mn}:{Sc}"

class HomePage(BaseHandler):
	def get(self):
		# render a list of recent posts
		
		recent_posts = cu.execute("""select * from posts order by date_published desc;""").fetchmany(5)
		recent = [Post(post) for post in recent_posts]
		page = dict(
			hero="you're home!"
			)
		self.render("index.html", recent=recent, page=page)

# authentication
class LoginHandler(BaseHandler):
	def get(self):
		page = dict(
			hero="just login"
			)
		self.render("login.html", error=None, page=page)
	
	def post(self):
		page = dict(
			hero="just log in"
			)
		user = cu.execute(f"""select * from users where username="{self.get_argument("username")}";""").fetchone()
		if not user:
			self.render("login.html", error="user not found", page=page)
			return
		else:
			user = User(user)
		
		if self.pswd_authenticated(self.get_argument("password"), user.password):
			self.set_secure_cookie("user", self.get_argument("username"))
			self.redirect("/")
		else:
			self.render("login.html", error="username and password don't match", page=page)

class LogoutHandler(BaseHandler):
	def get(self):
		self.clear_cookie("user")
		self.redirect("/")

class SignupHandler(BaseHandler):
	def get(self):
		page = dict(
			hero="please. welcome"
			)
		self.render("signup.html", error=None, page=page)
	
	def post(self):
		page = dict(
			hero="make yourself at home"
			)
		username = self.get_argument("username")
		
		if self.user_exists(username):
			self.render("signup.html", error="user already exists", page=page)
		else:
			password = hashlib.md5(self.get_argument("password").encode()).hexdigest()
			cu.execute(f"""insert into users(username, password) values("{username}", "{password}");""")
		db.commit()
		
		self.redirect("/login")

# app handlers
# posts.db == id, heading, content, author, date_published

# /posts/id -- single post
# /posts -- all posts
# /new-post -- add new post (auth)
# /posts/id/edit -- edit a post (auth)
# delete a post!

class PostHandler(BaseHandler):
	def get(self, post_id):
		page = dict(
			hero="the source"
			)
		post = cu.execute(f"""select * from posts where id={post_id};""").fetchone()
		
		# make a post class to ease access
		post = Post(post)
		self.render("post.html", post=post, page=page)

class AllPostsHandler(BaseHandler):
	def get(self):
		page = dict(
			hero="this is all of it"
			)
		all = cu.execute("""select * from posts order by date_published desc;""").fetchall()
		all = [Post(post) for post in all]
		self.render("posts.html", all=all, page=page)

class NewPostHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		page = dict(
			hero="make it happen"
			)
		self.render("new-post.html", error=None, page=page, redo=[False, ""])
	
	@tornado.web.authenticated
	def post(self):
		heading = self.get_argument("heading")
		content = self.get_argument("content")
		author = self.current_user.decode()
		pub_date = self.now()
		
		if heading != "":
			cu.execute(f"""insert into posts(heading, content, author, date_published) values("{heading}", "{content}", "{author}", "{pub_date}");""")
			db.commit()
		else:
			page = dict(
				hero="make it happen"
			)
			self.render("new-post.html", error="post heading is empty", page=page, redo=[True, content])
		
		self.redirect("/posts")

class EditPostHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self, post_id):
		page = dict(
			hero="make your adjustments"
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

class PostDeleteHandler(BaseHandler):
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
		self.render("profile.html", page=page)

app = tornado.web.Application(
	[
		(r"/", HomePage),
		(r"/login", LoginHandler),
		(r"/logout", LogoutHandler),
		(r"/signup", SignupHandler),
		(r"/posts/([0-9]+)", PostHandler),
		(r"/posts", AllPostsHandler),
		(r"/new-post", NewPostHandler),
		(r"/posts/([0-9]+)/edit", EditPostHandler),
		(r"/posts/([0-9]+)/edit/delete", PostDeleteHandler),
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

app.listen(8081)
tornado.ioloop.IOLoop.current().start()
	