# AS simple as possbile flask google oAuth 2.0
from flask import Flask, redirect, url_for, session, request, jsonify, Response
from authlib.integrations.flask_client import OAuth
import os
from flask_cors import CORS
from datetime import timedelta
import sys
from flask_cors import CORS, cross_origin
import psycopg2
from werkzeug.exceptions import HTTPException
import hashlib
import jwt
import urllib.parse as urlparse
from yahoo_fin.stock_info import get_live_price, get_quote_data

# dotenv setup
from dotenv import load_dotenv
load_dotenv()
# App config
app = Flask(__name__)
CORS(app)


url = urlparse.urlparse(os.environ['DATABASE_URL'])
dbname = url.path[1:]
user = url.username
password = url.password
host = url.hostname
port = url.port

con = psycopg2.connect(
    dbname=dbname,
    user=user,
    password=password,
    host=host,
    port=port
)

# con = psycopg2.connect(
#             dbname=chronicle.db
#             # user=user,
#             # password=password,
#             # host=host,
#             # port=port
#             )


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


def hasher(string):
    return hashlib.sha256(string.encode()).hexdigest()

# Generates a token for a registered user


def generate_token(username):
    """
    Generates a JSON Web Token (JWT) encoded token for a given username
    Input: username (str)
    Output: JWT-encoded token (str)
    """
    # private_key = "SecretKey"
    private_key = os.environ['PRIVATE_KEY']
    # private_key = "Hamster Wealth is the best website teeheexd"

    token = jwt.encode({'username': username}, private_key, algorithm='HS256')
    return token


# @app.route('/')
# def hello_world():
#     return redirect('/portfolios')
#     return dict(session)['token']['id_token']

# @app.route('/login')
# def login():
#     google = oauth.create_client('google')  # create the google oauth client
#     redirect_uri = url_for('authorize', _external=True)
#     return google.authorize_redirect(redirect_uri)


# @app.route('/authorize')
# def authorize():
#
#     cur = con.cursor()
#     google = oauth.create_client('google')  # create the google oauth client
#     # Access token from google (needed to get user info)
#     token = google.authorize_access_token()
#     # userinfo contains stuff u specificed in the scrope
#     resp = google.get('userinfo')
#     user_info = resp.json()
#     user = oauth.google.userinfo()  # uses openid endpoint to fetch user info
#     # Here you use the profile/user data that you got and query your database find/register the user
#     # and set ur own data in the session not the profile from google
#     session['token'] = token
#     session['user'] = user
#     # make the session permanant so it keeps existing after broweser gets closed
#     session.permanent = True

#     cur.execute('BEGIN TRANSACTION;')
#     query = """
#                 INSERT INTO client (token, name) VALUES ('{}', '{}');
#             """.format(dict(session)['token']['id_token'], dict(session)['user']['name'])
#     cur.execute(query)
#     cur.execute('COMMIT;')
#     # return dict(session)['token']['id_token']
#     return redirect('http://localhost:3000/portfolios')
#     # return redirect('http://localhost:3000/gettoken')


@app.route('/auth/login', methods=['POST'])
def auth_login():
    cur = con.cursor()
    data = request.get_json()
    if data['username'] is None or data['password'] is None:
        # raise InputError ('Please enter your username and password')
        raise InvalidUsage(
            'Please enter your username and password', status_code=400)
    query = """select token, password from client where username = '{}'; """.format(
        data['username'])
    cur.execute(query)
    x = cur.fetchone()
    if x is None:
        # raise AccessError ('Invalid username')
        raise InvalidUsage('Invalid username', status_code=403)
    token, password = x
    hashed_password = hasher(data['password'])
    if hashed_password != password:
        # raise AccessError ('Incorrect password')
        raise InvalidUsage('Incorrect password', status_code=403)

    return {'token': token}


@app.route('/auth/register', methods=['POST'])
def auth_register():
    cur = con.cursor()
    data = request.get_json()
    if data['username'] is None or data['password'] is None:
        # raise InputError ('Please fill in all details')
        raise InvalidUsage('Please fill in all details', status_code=400)
    # Checks if username is unique
    query = """select username from client where username = '{}'; """.format(
        data['username'])
    cur.execute(query)
    x = cur.fetchone()
    if x is not None:
        raise InvalidUsage('Username already taken', status_code=409)

    # # Checks if email is unique
    # query = """select email from client u where email = '{}'; """.format(data['email'])
    # cur.execute(query)
    # x = cur.fetchone()
    # if x is not None:
    #     raise InvalidUsage('Email already taken', status_code=409)

    hashed_password = hasher(data['password'])
    token = generate_token(data['username'])
    cur.execute('BEGIN TRANSACTION;')
    cur.execute(
        f"""INSERT INTO client (token, username, password) VALUES ('{token}', '{data['username']}', '{hashed_password}');""")
    cur.execute('COMMIT;')

    query = """select max(p.portfolio_id) from portfolio p;"""
    cur.execute(query)
    x = cur.fetchone()
    if x[0] is None:
        portfolio_id_tuple = 0
    else:
        portfolio_id_tuple = x[0]
    portfolio_id = portfolio_id_tuple
    portfolio_id += 1

    cur.execute('BEGIN TRANSACTION;')
    query = """INSERT INTO portfolio (token, portfolio_id, title, balance)
                VALUES ('{}', {}, '{}', 0);""".format(token, portfolio_id, 'Virtual Portfolio')
    cur.execute(query)
    cur.execute('COMMIT;')

    return {'token': token}


# @app.route('/gettoken', methods=['GET'])
#
# def hello_world():
#     return dict(session)['token']['id_token']


# @app.route('/logout')
# def logout():
#     for key in list(session.keys()):
#         session.pop(key)
#     return redirect('/')

@app.route('/portfolios/create', methods=['POST'])
def portfolios_create():
    cur = con.cursor()
    parsed_token = request.headers.get('Authorization')
    if parsed_token is None:
        raise InvalidUsage('Invalid Auth Token', status_code=403)

    query = """select max(p.portfolio_id) from portfolio p;"""
    cur.execute(query)
    x = cur.fetchone()
    if x[0] is None:
        portfolio_id_tuple = 0
    else:
        portfolio_id_tuple = x[0]
    portfolio_id = portfolio_id_tuple
    portfolio_id += 1
    # print(portfolio_id)
    query = f"""select max(portfolio_id) from portfolio where token = '{parsed_token}';"""
    cur.execute(query)
    x = cur.fetchone()
    if x[0] is None:
        priv_portfolio_id_tuple = 0
    else:
        priv_portfolio_id_tuple = x[0]
    priv_portfolio_id = priv_portfolio_id_tuple
    priv_portfolio_id += 1
    # print(priv_portfolio_id)
    title = f'Portfolio {priv_portfolio_id}'
    cur.execute('BEGIN TRANSACTION;')
    query = """INSERT INTO portfolio (token, portfolio_id, title, balance)
                VALUES ('{}', {}, '{}', 0);""".format(parsed_token, portfolio_id, title)
    cur.execute(query)
    cur.execute('COMMIT;')

    return {
        'portfolio_id': portfolio_id
    }


@app.route('/portfolio/addcash', methods=['POST'])
def portfolio_addcash():
    cur = con.cursor()
    parsed_token = request.headers.get('Authorization')
    if parsed_token is None:
        raise InvalidUsage('Invalid Auth Token', status_code=403)
    data = request.get_json()
    if data is None:
        raise InvalidUsage('Malformed Requesta', status_code=400)
    if len(data) != 2:
        raise InvalidUsage('Malformed Requestb', status_code=400)

    portfolio_id = data['portfolio_id']
    cash_amt = data['cash_amount']
    cur.execute(
        f"select token from portfolio  where portfolio_id = '{portfolio_id}'")
    x = cur.fetchone()
    if x is None:
        raise InvalidUsage('Invalid Token', status_code=403)
    if isinstance(portfolio_id, int) is False:
        raise InvalidUsage('Malformed Request', status_code=400)

    if isinstance(cash_amt, int) is False and isinstance(cash_amt, float) is False:
        raise InvalidUsage('Malformed Request', status_code=400)

    cur.execute(
        f"select portfolio_id from portfolio where token = '{parsed_token}'")
    portfolio_found = 0
    x = cur.fetchall()
    for pid in x:
        if portfolio_id == pid[0]:
            portfolio_found = 1
            break
    if portfolio_found == 0:
        raise InvalidUsage('Portfolio not found', status_code=404)

    cur.execute(
        f"select balance from portfolio where token = '{parsed_token}' and portfolio_id = {portfolio_id}")
    balance = cur.fetchone()

    cur.execute('BEGIN TRANSACTION;')
    query = f"""UPDATE portfolio
                SET  balance = {balance[0] + cash_amt}
                WHERE token = '{parsed_token}' and portfolio_id = {portfolio_id};"""
    cur.execute(query)
    cur.execute('COMMIT;')

    cur.execute(
        f"select balance from portfolio where token = '{parsed_token}' and portfolio_id = {portfolio_id}")
    balance = cur.fetchone()
    return {
        'balance': balance[0]
    }


@app.route('/portfolio/getbalance', methods=['GET'])
def portfolio_getbalance():
    cur = con.cursor()
    parsed_token = request.headers.get('Authorization')
    data = request.args.get('portfolio_id')
    if parsed_token is None:
        raise InvalidUsage('Invalid Auth Token', status_code=403)

    portfolio_id = int(data)

    cur.execute(
        f"select token from portfolio where portfolio_id = {portfolio_id}")
    x = cur.fetchone()
    if x is None:
        raise InvalidUsage(f'Invalid Token {parsed_token}', status_code=403)

    if data.isnumeric() is False:
        raise InvalidUsage('Malformed Request', status_code=400)

    cur.execute(
        f"select portfolio_id, title, balance from portfolio where token = '{parsed_token}'")
    portfolio_found = 0
    x = cur.fetchall()
    for pid in x:
        if portfolio_id == pid[0]:
            portfolio_found = 1

    if portfolio_found == 0:
        raise InvalidUsage(
            f'Portfolio not found {portfolio_id}', status_code=404)

    cur.execute(
        f"select balance from portfolio where token = '{parsed_token}' and portfolio_id = {portfolio_id}")
    balance = cur.fetchone()
    return {
        'balance': balance[0]
    }


@app.route('/portfolios/list', methods=['GET'])
def portfolios_list():
    cur = con.cursor()
    parsed_token = request.headers.get('Authorization')
    if parsed_token is None:
        raise InvalidUsage('Invalid Auth Token', status_code=403)
    cur.execute(
        f"select portfolio_id, title from portfolio where token = '{parsed_token}'")
    list_of_portfolio = cur.fetchall()

    portfolio_list = [
        {
            "portfolio_id": portfolio_deets[0],
            "title": portfolio_deets[1],
        }
        for portfolio_deets in list_of_portfolio
    ]

    return {'portfolio_list': portfolio_list}


# @app.route('/portfolios/edit')
# def portfolios_edit():
#     cur = con.cursor()
#     parsed_token = request.headers.get('Authorization')
#     if parsed_token is None:
#         raise InvalidUsage('Invalid Auth Token', status_code=403)

#     data = request.get_json()

#     portfolio_id = data['portfolio_id']
#     title = data['title']

#     cur.execute(
#         f"select token from portfolio  where portfolio_id = '{portfolio_id}'")
#     x = cur.fetchone()
#     if x is None:
#         raise InvalidUsage('Invalid Token', status_code=403)
#     if data['portfolio_id'].isnumeric() is False:
#         raise InvalidUsage('Malformed Request', status_code=400)

#     cur.execute(
#         f'select portfolio_id, title, balance from portfolio where token = {parsed_token}')
#     portfolio_found = 0
#     x = cur.fetchall()
#     for pid in x:
#         if portfolio_id == pid[0]:
#             portfolio_found = 1
#             break
#     if portfolio_found == 0:
#         raise InvalidUsage('Portfolio not found', status_code=404)

#     cur.execute('BEGIN TRANSACTION;')
#     query = f"""UPDATE portfolio p
#                 SET  p.title = '{title}',
#                 WHERE p.token = {parsed_token} and p.portfolio_id = {portfolio_id};"""
#     cur.execute(query)
#     cur.execute('COMMIT;')

#     return {}


@app.route('/portfolios/removeportfolio', methods=['DELETE'])
def portfolios_removeportfolio():
    cur = con.cursor()
    parsed_token = request.headers.get('Authorization')
    if parsed_token is None:
        raise InvalidUsage('Invalid Auth Token', status_code=403)
    parsed_pid = int(request.args.get('portfolio_id'))
    portfolio_id = parsed_pid

    cur.execute(
        f"select token from portfolio  where portfolio_id = '{portfolio_id}'")
    x = cur.fetchone()
    if x is None:
        raise InvalidUsage('Invalid Token', status_code=403)

    if isinstance(portfolio_id, int) is False:
        raise InvalidUsage('Malformed Request', status_code=400)

    cur.execute(
        f"select portfolio_id, title, balance from portfolio where token = '{parsed_token}'")
    portfolio_found = 0
    x = cur.fetchall()
    for pid in x:
        if portfolio_id == pid[0]:
            portfolio_found = 1
            break
    if portfolio_found == 0:
        raise InvalidUsage('Portfolio not found', status_code=404)

    cur.execute('BEGIN TRANSACTION;')
    query = f"""DELETE FROM portfolio
                WHERE portfolio.portfolio_id = {portfolio_id} and portfolio.token = '{parsed_token}';"""
    cur.execute(query)
    cur.execute('COMMIT;')
    return {}


@app.route('/portfolio/buyholding', methods=['POST'])
def portfolio_buyholding():
    cur = con.cursor()
    parsed_token = request.headers.get('Authorization')
    if parsed_token is None:
        raise InvalidUsage('Invalid Auth Token', status_code=403)
    data = request.get_json()
    portfolio_id = int(data['portfolio_id'])
    ticker = str(data['ticker'].upper())
    avg_price = float(data['avg_price'])
    quantity = int(data['quantity'])

    query = f"select token from portfolio where portfolio_id = {portfolio_id};"
    cur.execute(query)
    x = cur.fetchone()
    if x is None:
        raise InvalidUsage('Invalid Token', status_code=403)

    if isinstance(portfolio_id, int) is False and isinstance(quantity, int) is False and isinstance(avg_price, float) is False:
        raise InvalidUsage('Malformed Request', status_code=400)

    try:
        data = get_live_price(f'{ticker}')
    except:
        raise InvalidUsage('Invalid Ticker', status_code=404)

    cur.execute(
        f"select portfolio_id from portfolio where token = '{parsed_token}'")
    portfolio_found = 0
    x = cur.fetchall()
    for pid in x:
        if portfolio_id == pid[0]:
            portfolio_found = 1
            break
    if portfolio_found == 0:
        raise InvalidUsage('Portfolio not found', status_code=404)
    # Error trapping ^

    # Check is stock owned
    cur.execute(
        f'select ticker from stock where portfolio_id = {portfolio_id}')
    x = cur.fetchall()
    ticker_found = 0
    for stock in x:
        if ticker == stock[0]:
            ticker_found = 1
            break

    if quantity <= 0:
        raise InvalidUsage('Invalid quantity', status_code=404)
    if avg_price <= 0:
        raise InvalidUsage('Invalid price', status_code=404)

    # deduct from balance
    cur.execute(
        f"select balance from portfolio where token = '{parsed_token}' and portfolio_id = {portfolio_id}")
    balance = cur.fetchone()
    cash_amt = avg_price * quantity
    cash_amt = round(cash_amt, 2)
    if int(cash_amt > balance[0]):
        raise InvalidUsage(
            f'Not enough cash in balance', status_code=404)
    cur.execute('BEGIN TRANSACTION;')
    query = f"""UPDATE portfolio
                SET  balance = {balance[0] - cash_amt}
                WHERE portfolio_id = {portfolio_id};"""
    cur.execute(query)
    cur.execute('COMMIT;')

    # if not owned add to portfolio
    if ticker_found == 0:
        company = get_quote_data(f'{ticker}')['longName']
        cur.execute('BEGIN TRANSACTION;')
        query = f"""INSERT INTO stock (portfolio_id, ticker, company, avg_price, units)
                    VALUES ({portfolio_id}, '{ticker.upper()}', '{company}', {avg_price}, {quantity});"""
        cur.execute(query)
        cur.execute('COMMIT;')
    else:
        # if owned, update units and avg price
        cur.execute(
            f"select avg_price, units from stock where portfolio_id = {portfolio_id} and ticker = '{ticker}'")
        x = cur.fetchone()
        old_avg_price, old_units = x
        new_avg_price = ((old_avg_price * old_units) +
                         (avg_price * quantity))/(quantity + old_units)
        new_avg_price = "{:.2f}".format(new_avg_price)
        cur.execute('BEGIN TRANSACTION;')
        query = f"""UPDATE stock
                    SET  avg_price = {new_avg_price},
                         units = {old_units + quantity}
                    WHERE portfolio_id = {portfolio_id} and ticker = '{ticker}';"""
        cur.execute(query)
        cur.execute('COMMIT;')
    return {}


@app.route('/portfolio/sellholding', methods=['PUT'])
def portfolio_sellholding():
    cur = con.cursor()
    parsed_token = request.headers.get('Authorization')
    if parsed_token is None:
        raise InvalidUsage('Invalid Auth Token', status_code=403)
    data = request.get_json()
    portfolio_id = int(data['portfolio_id'])
    ticker = str(data['ticker'].upper())
    avg_price = float(data['avg_price'])
    quantity = int(data['quantity'])

    query = f"select token from portfolio where portfolio_id = {portfolio_id};"
    cur.execute(query)
    x = cur.fetchone()
    if x is None:
        raise InvalidUsage('Invalid Token', status_code=403)

    if isinstance(portfolio_id, int) is False and isinstance(quantity, int) is False and isinstance(avg_price, float) is False:
        raise InvalidUsage('Malformed Request', status_code=400)
    if ticker.isalpha() is False:
        raise InvalidUsage('Malformed Request', status_code=400)

    cur.execute(
        f"select portfolio_id from portfolio where token = '{parsed_token}'")
    portfolio_found = 0
    x = cur.fetchall()
    for pid in x:
        if portfolio_id == pid[0]:
            portfolio_found = 1
            break
    if portfolio_found == 0:
        raise InvalidUsage('Portfolio not found', status_code=404)
    # Error trapping ^

    # Check is stock owned
    cur.execute(
        f'select ticker from stock where portfolio_id = {portfolio_id}')
    x = cur.fetchall()
    ticker_found = 0
    for stock in x:
        if ticker == stock[0]:
            ticker_found = 1
            break
    if ticker_found == 0:
        raise InvalidUsage('Insufficient shares', status_code=404)

    if quantity <= 0:
        raise InvalidUsage('Invalid quantity', status_code=404)
    if avg_price <= 0:
        raise InvalidUsage('Invalid price', status_code=404)

    cur.execute(
        f"select units from stock where portfolio_id = {portfolio_id} and ticker = '{ticker}'")
    x = cur.fetchone()
    units = x[0]

    # if not owned add to portfolio
    if quantity == units:
        company = get_quote_data(f'{ticker}')['longName']
        cur.execute('BEGIN TRANSACTION;')
        query = f"""delete from stock where ticker = '{ticker}' and portfolio_id = {portfolio_id};"""
        cur.execute(query)
        cur.execute('COMMIT;')
    elif quantity < units:
        # if owned, update units and avg price
        cur.execute(
            f"select units from stock where portfolio_id = {portfolio_id} and ticker = '{ticker}'")
        x = cur.fetchone()
        old_units = x
        cur.execute('BEGIN TRANSACTION;')
        query = f"""UPDATE stock
                    SET  units = {old_units[0] - quantity}
                    WHERE portfolio_id = {portfolio_id} and ticker = '{ticker}';"""
        cur.execute(query)
        cur.execute('COMMIT;')
    else:
        raise InvalidUsage('Insufficient shares', status_code=404)

    # add to balance
    cur.execute(
        f"select balance from portfolio where token = '{parsed_token}' and portfolio_id = {portfolio_id}")
    balance = cur.fetchone()
    cash_amt = avg_price * quantity
    cash_amt = round(cash_amt, 2)
    if int(cash_amt > balance[0]):
        raise InvalidUsage(
            f'Not enough cash in balance', status_code=404)
    cur.execute('BEGIN TRANSACTION;')
    query = f"""UPDATE portfolio
                SET  balance = {balance[0] + cash_amt}
                WHERE portfolio_id = {portfolio_id};"""
    cur.execute(query)
    cur.execute('COMMIT;')

    return {}


@app.route('/portfolio/deleteholding', methods=['DELETE'])
def portfolio_deleteholding():
    cur = con.cursor()
    parsed_token = request.headers.get('Authorization')
    if parsed_token is None:
        raise InvalidUsage('Invalid Auth Token', status_code=403)
    data = request.get_json()
    portfolio_id = int(data['portfolio_id'])
    ticker = str(data['ticker'].upper())
    avg_price = float(data['avg_price'])
    quantity = int(data['quantity'])

    query = f"select token from portfolio where portfolio_id = {portfolio_id};"
    cur.execute(query)
    x = cur.fetchone()
    if x is None:
        raise InvalidUsage('Invalid Token', status_code=403)

    if isinstance(portfolio_id, int) is False and isinstance(quantity, int) is False and isinstance(avg_price, float) is False:
        raise InvalidUsage('Malformed Request', status_code=400)
    if ticker.isalpha() is False:
        raise InvalidUsage('Malformed Request', status_code=400)

    cur.execute(
        f"select portfolio_id from portfolio where token = '{parsed_token}'")
    portfolio_found = 0
    x = cur.fetchall()
    for pid in x:
        if portfolio_id == pid[0]:
            portfolio_found = 1
            break
    if portfolio_found == 0:
        raise InvalidUsage('Portfolio not found', status_code=404)
    # Error trapping ^

    # Check is stock owned
    cur.execute(
        f'select ticker from stock where portfolio_id = {portfolio_id}')
    x = cur.fetchall()
    ticker_found = 0
    for stock in x:
        if ticker == stock[0]:
            ticker_found = 1
            break
    if ticker_found == 0:
        raise InvalidUsage(
            'You do not own any shares of this stock', status_code=404)

    cur.execute('BEGIN TRANSACTION;')
    query = f"""delete from stock where ticker = '{ticker}' and portfolio_id = {portfolio_id};"""
    cur.execute(query)
    cur.execute('COMMIT;')

    return {}


@app.route('/portfolio/holdings', methods=['GET'])
def portfolio_holdings():
    cur = con.cursor()
    parsed_token = request.headers.get('Authorization')
    parsed_pid = int(request.args.get('portfolio_id'))
    if parsed_token is None:
        raise InvalidUsage('Invalid Auth Token', status_code=403)
    cur.execute(
        f"select token from portfolio  where portfolio_id = {parsed_pid}")
    x = cur.fetchone()
    if x is None:
        raise InvalidUsage('Invalid Token', status_code=403)

    cur.execute(
        f"select portfolio_id from portfolio where token = '{parsed_token}'")
    portfolio_found = 0
    x = cur.fetchall()
    for pid in x:
        if parsed_pid == pid[0]:
            portfolio_found = 1
            break
    if portfolio_found == 0:
        raise InvalidUsage('Portfolio not found', status_code=404)

    cur.execute(
        f"select ticker, company, avg_price, units from stock  where portfolio_id = {parsed_pid}")
    x = cur.fetchall()

    stock_list = []

    assets = 0
    for stock in x:
        ticker, company, avg_price, units = stock
        live_price = get_live_price(f'{ticker}')
        value = units * live_price
        assets += value

    for holding in x:
        ticker, company, avg_price, units = holding
        temp = get_quote_data(f'{ticker}')
        live_price = get_live_price(f'{ticker}')
        if live_price > 0:
            live_price = "{:.2f}".format(live_price)
        else:
            live_price = "{:.4f}".format(live_price)
        change_p = temp['regularMarketChangePercent']

        change_d = temp['regularMarketChange']

        if float(change_d) > 0:
            change_d = "{:.2f}".format(float(change_d))
        else:
            change_d = "{:.2g}".format(float(change_d))

        value = float(live_price) * int(units)
        value = "{:.2f}".format(value)
        profit_loss_d = float(value) - (units * avg_price)

        profit_loss_p = (profit_loss_d/(units * avg_price)) * 100
        # else:
        #     profit_loss_p = -1 * (100 - profit_loss_d/value)
        profit_loss_p = "{:.2f}".format(profit_loss_p)
        profit_loss_d = "{:.2f}".format(profit_loss_d)
        if float(profit_loss_d) < 0:
            profit_loss = f'-${-1*float(profit_loss_d)} ({profit_loss_p}%)'
        else:
            profit_loss = f'${float(profit_loss_d)} ({profit_loss_p}%)'

        change_value = float(change_d) * int(units)
        if float(change_value) > 0:
            change_value = "{:.2f}".format(float(change_value))
        else:
            change_value = "{:.2g}".format(float(change_value))
        weight = float(value)/assets * 100
        weight = "{:.2f}".format(weight)

        change_p = temp['regularMarketChangePercent']
        change_d = temp['regularMarketChange']
        change_p = "{:.2f}".format(change_p)
        change_d = "{:.5f}".format(change_d)
        if float(change_d) < 0:
            change = f'-${-1*float(change_d)} ({change_p}%)'
        else:
            change = f'${float(change_d)} ({change_p}%)'

        live_price_str = f'${live_price}'
        avg_price_str = f'${avg_price}'
        value_str = f'${float(value)}'

        if float(change_value) < 0:
            change_value_str = f'-${-1*float(change_value)}'
        else:
            change_value_str = f'${float(change_value)}'

        stock = {
            'ticker': ticker,
            'company': company,
            'live_price': live_price_str,
            'change': change,

            'profit_loss': profit_loss,
            'units': units,
            'avg_price': avg_price_str,
            'value': value_str,
            'weight': weight,
            'change_value': change_value_str
        }
        stock_list.append(stock)

    return {'holdings': stock_list}


# @app.route('/user/list')
# def user_list():
#
#     cur = con.cursor()
#     con.execute("""select client.username, portfolio.title, portfolio.portfolio_id from client join portfolio
#                     where client.token = portfolio.token; """)
#     x = cur.fetchall()
#     array_list = []
#     for portfolio in x:
#         name, title, pid = x
#         assets = 0
#         portfolio_chg = 0
#         con.execute(f"""select ticker, avg_price, units from stock where portfolio_id = {pid}""")
#         y = cur.fetchall()
#         for stock in y:
#             ticker, avg_price, units = y
#             value = get_live_price(f'{ticker}') * units
#             value = "{:.2f}".format(value)
#             asset += value

#         for stock in y:
#             ticker, avg_price, units = y
#             value = get_live_price(f'{ticker}') * units
#             value = "{:.2f}".format(value)
#             weight = value / assets
#             temp = get_quote_data(f'{ticker}')
#             change_p = temp['regularMarketChangePercent']
#             portfolio_chg += change_p * weight


if __name__ == '__main__':
    app.run(debug=True, port=4500)
