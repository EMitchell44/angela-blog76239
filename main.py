from flask import abort, Flask, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from functools import wraps
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CommentForm, CreatePostForm, LoginForm, RegisterForm
from flask_gravatar import Gravatar

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)
gravatar = Gravatar(
    app,
    size=100,
    rating='r',
    default='monsterid',
    force_default=False,
    force_lower=False,
    use_ssl=False,
    base_url=None
    )

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
login_manager = LoginManager(app)

##CONFIGURE TABLES

class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, ForeignKey('users.id'))
    author = relationship('User', back_populates='posts')
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    comments = relationship('Comment', back_populates='parent_post')

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(200), unique=True, nullable=False)
    name = db.Column(db.String(200), unique=False, nullable=False)
    password = db.Column(db.String(200), unique=False, nullable=False)
    posts = relationship('BlogPost', back_populates='author')
    comments = relationship('Comment', back_populates='author')

class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    comment = db.Column(db.String(), nullable=False)
    author_id = db.Column(db.Integer, ForeignKey('users.id'))
    author = relationship('User', back_populates='comments')
    post_id = db.Column(db.Integer, ForeignKey('blog_posts.id'))
    parent_post = relationship('BlogPost', back_populates='comments')

db.create_all()


def admin_only(f):
    @wraps(f)
    def admin_only(*args, **kwargs):
        if not current_user.id or current_user.id != 1:
            abort(403, 'Halt! Verboten!')
        return f(*args, **kwargs)
    return admin_only



@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts)

@app.route('/beluga')
@login_required
def beluga():
    return "It worked."


@app.route('/register', methods=['GET', 'POST'])
def register():
    # Joe's password is "QWERTY"
    # Sally's password is "QWERTY"
    # Jack's password is "QWERTY"
    form = RegisterForm()
    if form.validate_on_submit():
        for user in User.query.all():
            if user.email == form.email.data:
                flash('Email already registered. Please log in.')
                return redirect(url_for('login'))
        password = form.password.data

        new_user = User(
        email=form.email.data,
        name=form.name.data,
        password=generate_password_hash(
            password,
            method='pbkdf2:sha256',
            salt_length=8,
            )
        )
        db.session.add(new_user)
        db.session.commit()
        return redirect('/')
    return render_template("register.html", form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        for user in User.query.all():
            if user.email == form.email.data:
                if check_password_hash(user.password, form.password.data):
                    login_user(user)
                    return redirect('/')
                flash('Incorrect password.')
                return redirect(url_for('login'))
        flash('Email not registered.')
        return redirect(url_for('login'))
    return render_template("login.html", form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=['GET', 'POST'])
def show_post(post_id):
    form = CommentForm()
    requested_post = BlogPost.query.get(post_id)
    if form.validate_on_submit():
        if current_user.is_authenticated:
            new_comment = Comment(
                comment=form.comment.data,
                author_id=current_user.id,
                post_id=post_id,
            )
            #comment = db.Column(db.String(), nullable=False)
            #author_id = db.Column(db.Integer, ForeignKey('users.id'))
            #author = relationship('User', back_populates='comments')
            #post_id = db.Column(db.Integer, ForeignKey('blog_posts.id'))
            #parent_post = relationship('BlogPost', back_populates='comments')

            db.session.add(new_comment)
            db.session.commit()

    return render_template("post.html", post=requested_post, form=form)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/new-post", methods=['GET', 'POST'])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


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

    return render_template("make-post.html", form=edit_form)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

if __name__ == "__main__":
    app.run(host='127.0.0.1', port=5000)
