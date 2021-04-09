from flask import Flask, request, url_for, redirect, jsonify, session
from flask_cors import CORS
import sqlite3,sys
import psycopg2
from werkzeug.exceptions import HTTPException
import hashlib
import jwt
from flask_cors import CORS, cross_origin
from authlib.integrations.flask_client import OAuth
app = Flask(__name__)
app.secret_key = 'hamsterwealth216,!'
CORS(app)
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id='912573563558-gim00oo0d5f34ui7m78j1q2vldivqrvd.apps.googleusercontent.com',
    client_secret='9Xp8msoSc8EI4pdGhqQyV6zU',
    access_token_url='https://accounts.google.com/o/oauth2/token',
    access_token_params=None,
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    authorize_params=None,
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    userinfo_endpoint='https://openidconnect.googleapis.com/v1/userinfo',  # This is only needed if using openId to fetch user info
    client_kwargs={'scope': 'openid email profile'},
)

con = psycopg2.connect(
            dbname=chronicle.db
            # user=user,
            # password=password,
            # host=host,
            # port=port
            )

class InvalidUsage(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv

@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


@app.route('/login')
def login():
    google = oauth.create_client('google')
    redirect_uri = url_for('authorize', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/authorize')
def authorize():
    google = oauth.create_client('google')
    token = google.authorize_access_token()
    resp = google.get('userinfo')
    resp.raise_for_status() # not in tutorial
    user_info = resp.json()
    # do something with the token and profile
    return redirect('/')

@app.route('/logout')
def logout():
    for key in list(session.keys()):
        session.pop(key)
    return redirect('/')

# @app.route('portfolio/addcash')
# @cross_origin()
# def portfolio_addcash():

# @app.route('portfolio/getbalance')
# @cross_origin()
# def portfolio_getbalance():

# @app.route('portfolio/buyholding')
# @cross_origin()
# def portfolio_buyholding():

# @app.route('portfolio/sellholding')
# @cross_origin()
# def portfolio_sellholding():

# @app.route('portfolio/deleteholding')
# @cross_origin()
# def portfolio_deleteholding():

# @app.route('portfolio/holdings')
# @cross_origin()
# def portfolio_holdings():

# @app.route('portfolios/list')
# @cross_origin()
# def portfolios_list():

# @app.route('portfolios/create')
# @cross_origin()
# def portfolios_create():

# @app.route('portfolios/edit')
# @cross_origin()
# def portfolios_edit():

# @app.route('portfolios/removeportfolio')
# @cross_origin()
# def portfolios_removeportfolio():

# @app.route('user/list')
# @cross_origin()
# def user_list():

