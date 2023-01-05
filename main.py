# from tkinter.tix import Form
from flask import Flask, render_template, redirect, url_for, flash, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from sqlalchemy import ForeignKey
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar
from functools import wraps
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")
ckeditor = CKEditor(app)
Bootstrap(app)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URI")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


##CONFIGURE TABLES

class BlogPost(db.Model):  # type: ignore
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    author_post = relationship("User", back_populates="post")
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    comment_post = relationship("Comment", back_populates="post_com")
    
class User(UserMixin, db.Model): # type: ignore
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))
    post = relationship("BlogPost", back_populates="author_post")
    comment = relationship("Comment", back_populates="author_com")
    
class Comment(db.Model): # type: ignore
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    author_com = relationship("User", back_populates="comment")
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    post_com = relationship("BlogPost", back_populates="comment_post")
    com = db.Column(db.Text)
    
# db.create_all()

# Security
def admin_only(func):
    @wraps(func)
    def check_admin(*args, **kwargs):
        if current_user.id!=1:
            return abort(403)
        return func(*args, **kwargs)
    return check_admin

# Flask Login Management
lg=LoginManager()
lg.init_app(app)

@lg.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)

@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts, currentuser=current_user)


@app.route('/register', methods=["POST", "GET"])
def register():
    regform=RegisterForm()
    if regform.validate_on_submit():
        if User.query.filter_by(email=regform.email.data).first():
            flash('You have already signed in with this email, please log in instead!')
            return redirect(url_for('login'))
        hashsalt=generate_password_hash(
            password=regform.password.data,   # type: ignore
            method="pbkdf2:sha256", 
            salt_length=8
        )
        newuser=User(
            name = regform.name.data,
            email = regform.email.data,
            password = hashsalt
        )
        db.session.add(newuser)
        db.session.commit()
        login_user(newuser)
        return redirect(url_for("get_all_posts"))
    return render_template("register.html", regform=regform, currentuser=current_user)


@app.route('/login', methods=["POST", "GET"])
def login():
    logform=LoginForm()
    if logform.validate_on_submit():
        email1=logform.email.data
        password1=logform.password.data
        userinfo = User.query.filter_by(email=email1).first()
        if not userinfo:
            flash("That email does not exist, please try again.")
            return redirect(url_for("login"))
        elif not check_password_hash(pwhash=userinfo.password, password=password1):
            flash("Password incorrect. please try again.")
            return redirect(url_for("login"))
        else:
            login_user(userinfo)
            return redirect(url_for("get_all_posts"))
    return render_template("login.html", form=logform, currentuser=current_user)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def show_post(post_id):
    requested_post = BlogPost.query.get(post_id)
    commentall= Comment.query.all()
    comm=CommentForm()
    if comm.validate_on_submit():
        if current_user.is_authenticated:
            cm=Comment(
                author_id =current_user.id,
                post_id = post_id,
                com = comm.com.data
            )
            db.session.add(cm)
            db.session.commit()
            return redirect(url_for("show_post", post_id=post_id))
        else:
            flash("You need to register or login before you can comment on this post")
            return redirect(url_for("login"))
    return render_template("post.html", post=requested_post, currentuser=current_user, comform=comm, allcomment=commentall)


@app.route("/about")
def about():
    return render_template("about.html", currentuser=current_user)


@app.route("/contact")
def contact():
    return render_template("contact.html", currentuser=current_user)


@app.route("/new-post", methods=['POST','GET'])
# @admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            author_id=current_user.id,
            img_url=form.img_url.data,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form, p=0, currentuser=current_user)


@app.route("/edit-post/<int:post_id>", methods=['POST','GET'])
# @admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        body=post.body
    )
    if edit_form.validate_on_submit():
        print("Started")
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.body = edit_form.body.data
        print("Working")
        db.session.commit()
        print("Successful")
        return redirect(url_for("show_post", post_id=post_id))
    return render_template("make-post.html", form=edit_form, p=post_id, currentuser=current_user)


@app.route("/delete/<int:post_id>")
# @admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=os.environ.get('DEBUG'))
