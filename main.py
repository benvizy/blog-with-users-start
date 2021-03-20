from flask import Flask, render_template, redirect, url_for, flash
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegiForm, LoginForm, CommentForm
from flask_gravatar import Gravatar
from functools import wraps
from flask import abort
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")
ckeditor = CKEditor(app)
Bootstrap(app)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL", "sqlite:///blog.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

#LOGIN MANAGER
login_manager = LoginManager()
login_manager.init_app(app)

# Gravatar
gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

# ADMIN DECORATOR
# @admin_only
def admin_only(function):
    @wraps(function)
    def wrapper_function():
        if current_user.id != 1:
            return abort(403)
        return function()
    return wrapper_function



##CONFIGURE TABLES

class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.String(250), nullable=False)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    writer = relationship("User", back_populates="blogs")
    comments = relationship("Comment", back_populates="blog")

class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(75), unique=True, nullable=False)
    name = db.Column(db.String(50), unique=True, nullable=False)
    passy = db.Column(db.String(250), unique=True, nullable=False)
    blogs = relationship("BlogPost", back_populates="writer")
    comments = relationship("Comment", back_populates="commenter")

class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    blog_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    blog = relationship("BlogPost", back_populates="comments")
    commenter = relationship("User", back_populates="comments")


# db.create_all()

@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts, user=current_user)


@app.route('/register', methods=["POST", "GET"])
def register():
    form = RegiForm()
    if form.validate_on_submit():
        email = form.email.data
        passy = generate_password_hash(form.passy.data, method="pbkdf2:sha256", salt_length=8)
        name = form.name.data
        if User.query.filter_by(email=email).first():
            flash("There's already an account for this email.  Why don't ya log in ya booby?")
            return redirect(url_for('login'))
        elif User.query.filter_by(name=name).first():
            flash("This name is taken.  Be unique!")
            return render_template(url_for('register'))
        else:
            new_user = User(email=email, passy=passy, name=name)
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for('get_all_posts'))
    return render_template("register.html", form=form, user=current_user)


@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        passy = form.passy.data
        try:
            user = User.query.filter_by(email=email).first()
        except:
            flash('There is no email for that user!')
            return redirect(url_for('login'))
        else:
            if check_password_hash(user.passy, passy):
                login_user(user)
                return redirect(url_for('get_all_posts'))
    return render_template("login.html", form=form, user=current_user)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def show_post(post_id):
    requested_post = BlogPost.query.get(post_id)
    comment_form = CommentForm()
    if comment_form.validate_on_submit():
        if not current_user.is_authenticated:
            flash('you have got to login, bucko.  to make a post')
            return redirect(url_for('login'))
        text = comment_form.body.data
        new_comment = Comment(
            text=text,
            blog=requested_post,
            commenter=current_user
        )
        db.session.add(new_comment)
        db.session.commit()
        return render_template("post.html", post=requested_post, user=current_user, comment_form=comment_form)
    return render_template("post.html", post=requested_post, user=current_user, comment_form=comment_form)


@app.route("/about")
def about():
    return render_template("about.html", user=current_user)


@app.route("/contact")
def contact():
    return render_template("contact.html", user=current_user)


@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            writer=current_user.id,
            date=date.today().strftime("%B %d, %Y"),
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form, user=current_user)


@app.route("/edit-post/<int:post_id>")
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form, user=current_user)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
