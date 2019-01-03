from flask import Flask, render_template, redirect, url_for, request,flash
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm 
from wtforms import StringField, PasswordField, BooleanField
from wtforms.validators import InputRequired, Email, Length
from flask_sqlalchemy  import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from sqlalchemy.exc import IntegrityError
from flask_sqlalchemy import SQLAlchemy
import flask_login, flask, datetime
import os

#initialise flask application
app = Flask(__name__)

#adding sqlite database
project_dir = os.path.dirname(os.path.abspath(__file__))
print("path:",project_dir)
database_file = "sqlite:///{}".format(os.path.join(project_dir, "flaskdatabase.db"))
app.config["SQLALCHEMY_DATABASE_URI"] = database_file
app.config['SECRET_KEY'] = 'Thisissupposedtobesecret!'
bootstrap = Bootstrap(app)

#initialise connection to database
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


#Creating model Book that holds key, value and username. 
class Book(db.Model):
    __tablename__ = 'Book'
    key = db.Column(db.String(80), unique=True, nullable=False, primary_key=True)
    value = db.Column(db.String(80), unique=False, nullable=True)
    username = db.Column(db.String(15), db.ForeignKey('User.username',ondelete="CASCADE"), nullable=False) 
    
    def __repr__(self):
        return "<key: {0}, value:{1}, User: {2} >".format(self.key,self.value,self.username)

#User model to save registration information.
class User(UserMixin, db.Model):
    __tablename__ = 'User'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(15), unique=True)
    email = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(80))

#login form inherits from flaskform and has username, password and remember me field.
#displays message if wrong username is given.
class LoginForm(FlaskForm):
    username = StringField('username', validators=[InputRequired(), Length(min=4, max=15)])
    password = PasswordField('password', validators=[InputRequired(), Length(min=8, max=80)])
    remember = BooleanField('remember me')

    def validate_username(self, field):
        user = User.query.filter(User.username == self.username.data).first()
        if not user:
            raise ValueError("Invalid username.")

#Signup form with 3 required fields to register.
#displays error message when duplicate name or email is chosen.     
class RegisterForm(FlaskForm):
    email = StringField('email', validators=[InputRequired(), Email(message='Invalid email'), Length(max=50)])
    username = StringField('username', validators=[InputRequired(), Length(min=4, max=15)])
    password = PasswordField('password', validators=[InputRequired(), Length(min=8, max=80)])

    def validate_email(self, field):
        user = User.query.filter(User.email == self.email.data).first()
        if user:
            raise ValueError("Email account already exist.")
    def validate_username(self, field):
        user = User.query.filter(User.username == self.username.data).first()
        if user:
            raise ValueError("Username is taken, choose a different one.")

    

#Receive inputs from user creates objects(record) and sets in database. 
#Reads and displays all existing records. 
@app.route('/set', methods=["GET", "POST"])
@login_required
def set():
    record = None
    if request.form:
        try:
            record = Book(key=request.form.get("key"),value=request.form.get("value"),username=current_user.username)
            db.session.add(record)
            db.session.commit()
        except IntegrityError:
            print("Failed to add record")
            db.session.rollback()
            return "<h3> key already exists go back to add new one.</h3>"
    record = Book.query.filter_by(username=current_user.username).all()
    print("in home")
    return render_template("set.html", record=record)

#Gets a key from user and shows its respective value.
@app.route("/get", methods=["GET", "POST"])
@login_required
def get():
    print("at get home 1")
    empty=None        
    record = None    
    if request.form:
        print("form recognised")
        try:
            ti = request.form["key"]
            record = Book.query.filter_by(key=ti,username=current_user.username).first()
            if record is None:
                empty = "No record for the input key, try new one."
            
        except Exception as e:
            print("Couldn't find key")
            print(e)
    else: print("no request.form")
    return render_template("get.html", record=record,empty=empty)#redirect("/")

#Updates existing value fields
@app.route("/update", methods=["POST"])
def update():
    print("at update")
    try:
        newvalue = request.form.get("newvalue")
        oldvalue = request.form.get("oldvalue")
        record = Book.query.filter_by(value=oldvalue).first()
        record.value = newvalue
        db.session.commit()
    except Exception as e:
        print("Couldn't update Value")
        print(e)
    return redirect("/set")

#Deletes records
@app.route("/delete", methods=["POST"])
def delete():
    print("in delete")
    key = request.form.get("key")
    value=request.form.get("value")
    record = Book.query.filter_by(key=key,value=value,username=current_user.username).first()
    db.session.delete(record)
    db.session.commit()
    return redirect("/set")

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

#home page
@app.route('/')
def index():
    return render_template('index.html')

#login with userid and password, redirects to get page
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            if check_password_hash(user.password, form.password.data):
                login_user(user, remember=form.remember.data)
                return redirect(url_for('get'))
            else:
                return '<h1> Invalid Password</h1>'

        return '<h1>Invalid Username </h1>'
        
    return render_template('login.html', form=form)

#register to create an account, redirects to login page
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = RegisterForm()
    resignmsg = None
    
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data, method='sha256')
        new_user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(new_user)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            print("integrity error")
            resignmsg= "Username or Email id already in use. Choose a new one to register"
            return render_template("signup.html",form=form, resignmsg =resignmsg )
        flash('You were successfully registered')
        return redirect(url_for('login'))
        
    return render_template('signup.html', form=form)

#session timeout in 20 minutes of inactivity.
@app.before_request
def before_request():
    flask.session.permanent = True
    app.permanent_session_lifetime = datetime.timedelta(minutes=20)
    flask.session.modified = True
    flask.g.user = flask_login.current_user
    redirect(url_for('login'))
    
#Logout of the site and redirects to home.
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

#debug = True allows to see debug output in your console and within the web browser.
if __name__ == "__main__":
    app.run(debug=True)