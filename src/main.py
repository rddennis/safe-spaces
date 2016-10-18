from flask import Flask, render_template, request, flash, redirect, url_for
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.security import Security, SQLAlchemyUserDatastore, \
    UserMixin, RoleMixin, login_required, current_user
from flask_mail import Mail
from flask_security.forms import ConfirmRegisterForm, LoginForm
from wtforms import StringField
from wtforms.validators import Required, InputRequired
from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand
from datetime import datetime

import livereload
import psycopg2

# Create app
app = Flask(__name__)
app.config['DEBUG'] = True
app.config['SECRET_KEY'] = 'super-super-secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://localhost/hbcu-network'

app.config['SECURITY_REGISTERABLE'] = True 
app.config['SECURITY_RECOVERABLE'] = True 
app.config['SECURITY_CHANGEABLE'] = True 
app.config['SECURITY_CONFIRMABLE'] = True

app.config['SECURITY_EMAIL_SUBJECT_REGISTER'] = "Welcome to HBCU Safe Spaces!"
app.config['SECURITY_EMAIL_SUBJECT_PASSWORD_NOTICE'] = "Your HBCU Safe Spaces Password Has Changed."
app.config['SECURITY_EMAIL_SUBJECT_PASSWORD_RESET'] = "Change Your HBCU Safe Spaces Password"
app.config['SECURITY_EMAIL_SUBJECT_PASSWORD_CHANGE_NOTICE'] = "Your HBCU Safe Spaces Password Has Been Changed"
app.config['SECURITY_EMAIL_SUBJECT_CONFIRM'] = "Confirm Your HBCU Safe Spaces Email"

app.config['SECURITY_USER_IDENTITY_ATTRIBUTES'] =  ('username', 'email')

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_DEBUG'] = True
app.config['MAIL_USERNAME'] = 'ronesha@codeforprogress.org'
app.config['MAIL_PASSWORD'] = '07cb77nesh'

mail = Mail(app)

# Create database connection object
db = SQLAlchemy(app)
migrate = Migrate(app, db)
manager = Manager(app)
manager.add_command('db', MigrateCommand)


# Define models
roles_users = db.Table('roles_users',
        db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
        db.Column('role_id', db.Integer(), db.ForeignKey('role.id')))

posts_users = db.Table('posts_users',
		db.Column('post_id', db.Integer(), db.ForeignKey('post.id')),
		db.Column('user_id', db.Integer(), db.ForeignKey('user.id')))

friends = db.Table('friends',
    db.Column('friend_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('friended_id', db.Integer, db.ForeignKey('user.id'))
)

class ExtendedLoginForm(LoginForm):
    email = StringField('Username or Email Address', [InputRequired()])

class ExtendedConfirmRegisterForm(ConfirmRegisterForm):
    first_name = StringField('First Name', [Required()])
    last_name = StringField('Last Name', [Required()])
    university = StringField('University', [Required()])
    username = StringField('Username', [Required()])

class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer(), primary_key=True)
    first_name = db.Column(db.String(255))
    last_name = db.Column(db.String(255))
    username = db.Column(db.String(255), unique = True)
    email = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255))
    university = db.Column(db.String(255))
    active = db.Column(db.Boolean())
    confirmed_at = db.Column(db.DateTime())
    roles = db.relationship('Role', secondary=roles_users, backref=db.backref('users', lazy='dynamic'))
    friended = db.relationship('User', 
                               secondary=friends, 
                               primaryjoin=(friends.c.friend_id == id), 
                               secondaryjoin=(friends.c.friended_id == id), 
                               backref=db.backref('friends', lazy='dynamic'), 
                               lazy='dynamic')

    def follow(self, user):
        if not self.is_friend(user):
            self.friended.append(user)
            return self

    def unfollow(self, user):
        if self.is_friend(user):
            self.friended.remove(user)
            return self

    def is_friend(self, user):
        return self.friended.filter(friends.c.friended_id == user.id).count() > 0

class Post(db.Model):
	id = db.Column(db.Integer(), primary_key=True)
	post = db.Column(db.Text())
	timestamp = db.Column(db.DateTime())
	user = db.relationship('User', secondary=posts_users, backref=db.backref('posts', lazy='dynamic'))


# Setup Flask-Security
user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore, confirm_register_form=ExtendedConfirmRegisterForm, login_form=ExtendedLoginForm)

# Create a user to test with
# @app.before_first_request
# def create_user():
#     db.create_all()
#     user_datastore.create_user(email='ronesha@codeforprogress.org', password='')
#     db.session.commit()

# Views
@app.route('/')
@login_required
def home():
    return render_template('index.html')

@app.route('/timeline/<username>', methods=['GET', 'POST'])
@login_required
def timeline(username):
	all_content = Post.query.filter(User.username == username).join(Post.user)

	if request.method == 'POST':
		content = request.form['content']
		new_post = Post(post = content, timestamp = datetime.now())
		new_post.user.append(current_user)
		db.session.add(new_post)
		db.session.commit()
		return render_template('timeline.html', content = all_content, username=username)

	return render_template('timeline.html', content = all_content, username=username)


@app.route('/addfriend/<username>')
@login_required
def addfriend(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('User %s not found.' % username)
     	return redirect(url_for('home'))
    if user == current_user:
        flash('You can\'t follow yourself!')
       	return redirect(url_for('home'))
    g = User.query.filter(User.id == current_user.id).first()
    u = g.follow(user)
    if u is None:
        flash('Cannot follow ' + username + '.')
        return redirect(url_for('home'))
    db.session.add(u)
    db.session.commit()
    flash('You are now following ' + username + '!')
    return redirect(url_for('home'))

@app.route('/removefriend/<username>')
@login_required
def removefriend(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('User %s not found.' % username)
        return redirect(url_for('index'))
    if user == current_user:
        flash('You can\'t unfollow yourself!')
        return redirect(url_for('user', username=username))
    g = User.query.filter(User.id == current_user.id).first()
    u = g.unfollow(user)
    if u is None:
        flash('Cannot unfollow ' + nickname + '.')
        return redirect(url_for('user', username=username))
    db.session.add(u)
    db.session.commit()
    flash('You have stopped following ' + username + '.')
    return redirect(url_for('user', username=username))


@app.route('/logout')
def logout():
	logout()
	return render_template('index.html')

if __name__ == '__main__':
    app.run()
	# manager.run()
