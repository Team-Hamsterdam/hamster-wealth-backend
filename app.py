# AS simple as possbile flask google oAuth 2.0
from flask import Flask, redirect, url_for, session, request, jsonify
from authlib.integrations.flask_client import OAuth
import os
from datetime import timedelta
import sqlite3,sys
from flask_cors import CORS, cross_origin
import psycopg2
from werkzeug.exceptions import HTTPException
import hashlib
import jwt

from yahoo_fin.stock_info import get_live_price, get_quote_data

# dotenv setup
from dotenv import load_dotenv
load_dotenv()
# App config
app = Flask(__name__)
CORS(app)

# Session config
app.secret_key = '9Xp8msoSc8EI4pdGhqQyV6zU'
# app.secret_key = os.getenv("APP_SECRET_KEY")
app.config['SESSION_COOKIE_NAME'] = 'google-login-session'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=5)

# oAuth Setup
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
    # This is only needed if using openId to fetch user info
    userinfo_endpoint='https://openidconnect.googleapis.com/v1/userinfo',
    client_kwargs={'scope': 'openid email profile'},
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




# @app.route('/')
# def hello_world():
#     return redirect('/portfolios')
#     return dict(session)['token']['id_token']

@app.route('/login')
def login():
    google = oauth.create_client('google')  # create the google oauth client
    redirect_uri = url_for('authorize', _external=True)
    return google.authorize_redirect(redirect_uri)


@app.route('/authorize')
def authorize():
    con = sqlite3.connect('./chronicle.db')
    cur = con.cursor()
    google = oauth.create_client('google')  # create the google oauth client
    # Access token from google (needed to get user info)
    token = google.authorize_access_token()
    # userinfo contains stuff u specificed in the scrope
    resp = google.get('userinfo')
    user_info = resp.json()
    user = oauth.google.userinfo()  # uses openid endpoint to fetch user info
    # Here you use the profile/user data that you got and query your database find/register the user
    # and set ur own data in the session not the profile from google
    session['token'] = token
    session['user'] = user
    # make the session permanant so it keeps existing after broweser gets closed
    session.permanent = True

    cur.execute('BEGIN TRANSACTION;')
    query = """
                INSERT INTO client (token, name) VALUES ('{}', '{}');
            """.format(dict(session)['token']['id_token'], dict(session)['user']['name'])
    cur.execute(query)
    cur.execute('COMMIT;')

    return redirect('/portfolios')

@app.route('/gettoken')
def hello_world():
    return dict(session)['token']['id_token']


@app.route('/logout')
def logout():
    for key in list(session.keys()):
        session.pop(key)
    return redirect('/')

@app.route('/portfolios/create', methods=['POST'])
@cross_origin()
def portfolios_create():
    con = sqlite3.connect('./chronicle.db')
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
        'portfolio_id' : portfolio_id
    }

@app.route('/portfolio/addcash', methods=['POST'])
@cross_origin()
def portfolio_addcash():
    con = sqlite3.connect('./chronicle.db')
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
    cur.execute(f"select token from portfolio  where portfolio_id = '{portfolio_id}'")
    x = cur.fetchone()
    if x is None:
        raise InvalidUsage('Invalid Token', status_code=403)
    if isinstance(portfolio_id, int) is False:
        raise InvalidUsage('Malformed Request', status_code=400)

    if isinstance(cash_amt, int) is False and isinstance(cash_amt, float) is False:
        raise InvalidUsage('Malformed Request', status_code=400)




    cur.execute(f"select portfolio_id from portfolio where token = '{parsed_token}'")
    portfolio_found = 0
    x = cur.fetchall()
    for pid in x:
        if portfolio_id == pid[0]:
            portfolio_found = 1
            break
    if portfolio_found == 0:
        raise InvalidUsage('Portfolio not found', status_code=404)

    cur.execute(f"select balance from portfolio where token = '{parsed_token}' and portfolio_id = {portfolio_id}")
    balance = cur.fetchone()

    cur.execute('BEGIN TRANSACTION;')
    query = f"""UPDATE portfolio
                SET  balance = {balance[0] + cash_amt}
                WHERE token = "{parsed_token}" and portfolio_id = {portfolio_id};"""
    cur.execute(query)
    cur.execute('COMMIT;')

    cur.execute(f"select balance from portfolio where token = '{parsed_token}' and portfolio_id = {portfolio_id}")
    balance = cur.fetchone()
    return {
        'balance' : balance[0]
    }

@app.route('/portfolio/getbalance', methods=['GET'])
@cross_origin()
def portfolio_getbalance():
    con = sqlite3.connect('./chronicle.db')
    cur = con.cursor()
    parsed_token = request.headers.get('Authorization')
    data = request.args.get('query')
    if parsed_token is None:
        raise InvalidUsage('Invalid Auth Token', status_code=403)

    portfolio_id = int(data)

    cur.execute(f"select token from portfolio  where portfolio_id = {portfolio_id}")
    x = cur.fetchone()
    if x is None:
        raise InvalidUsage('Invalid Token', status_code=403)

    if data.isnumeric() is False:
        raise InvalidUsage('Malformed Request', status_code=400)

    cur.execute(f"select portfolio_id, title, balance from portfolio where token = '{parsed_token}'")
    portfolio_found = 0
    x = cur.fetchall()
    for pid in x:
        if portfolio_id == pid[0]:
            portfolio_found = 1

    if portfolio_found == 0:
        raise InvalidUsage(f'Portfolio not found {portfolio_id}', status_code=404)

    cur.execute(f"select balance from portfolio where token = '{parsed_token}' and portfolio_id = {portfolio_id}")
    balance = cur.fetchone()
    return {
        'balance' : balance[0]
    }

@app.route('/portfolios/list', methods=['GET'])
@cross_origin()
def portfolios_list():
    con = sqlite3.connect('./chronicle.db')
    cur = con.cursor()
    parsed_token = request.headers.get('Authorization')
    if parsed_token is None:
        raise InvalidUsage('Invalid Auth Token', status_code=403)
    cur.execute(f"select portfolio_id, title from portfolio where token = '{parsed_token}'")
    list_of_portfolio = cur.fetchall()

    portfolio_list = [
        {
            "portfolio_id": portfolio_deets[0],
            "title": portfolio_deets[1],
        }
        for portfolio_deets in list_of_portfolio
    ]

    return {'portfolio_list' : portfolio_list}

@app.route('/portfolios/edit')
@cross_origin()
def portfolios_edit():
    con = sqlite3.connect('./chronicle.db')
    cur = con.cursor()
    parsed_token = request.headers.get('Authorization')
    if parsed_token is None:
        raise InvalidUsage('Invalid Auth Token', status_code=403)

    data = request.get_json()

    portfolio_id = data['portfolio_id']
    title = data['title']

    cur.execute(f"select token from portfolio  where portfolio_id = '{portfolio_id}'")
    x = cur.fetchone()
    if x is None:
        raise InvalidUsage('Invalid Token', status_code=403)
    if data['portfolio_id'].isnumeric() is False:
        raise InvalidUsage('Malformed Request', status_code=400)


    cur.execute(f'select portfolio_id, title, balance from portfolio where token = {parsed_token}')
    portfolio_found = 0
    x = cur.fetchall()
    for pid in x:
        if portfolio_id == pid[0]:
            portfolio_found = 1
            break
    if portfolio_found == 0:
        raise InvalidUsage('Portfolio not found', status_code=404)

    cur.execute('BEGIN TRANSACTION;')
    query = f"""UPDATE portfolio p
                SET  p.title = '{title}',
                WHERE p.token = {parsed_token} and p.portfolio_id = {portfolio_id};"""
    cur.execute(query)
    cur.execute('COMMIT;')

    return {}

@app.route('/portfolios/removeportfolio')
@cross_origin()
def portfolios_removeportfolio():
    con = sqlite3.connect('./chronicle.db')
    cur = con.cursor()
    parsed_token = request.headers.get('Authorization')
    if parsed_token is None:
        raise InvalidUsage('Invalid Auth Token', status_code=403)

    data = request.get_json()
    portfolio_id = data['portfolio_id']

    cur.execute(f"select token from portfolio  where portfolio_id = '{portfolio_id}'")
    x = cur.fetchone()
    if x is None:
        raise InvalidUsage('Invalid Token', status_code=403)


    if portfolio_id.isnumeric() is False:
        raise InvalidUsage('Malformed Request', status_code=400)

    cur.execute(f'select portfolio_id, title, balance from portfolio where token = {parsed_token}')
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


@app.route('/portfolio/buyholding')
@cross_origin()
def portfolio_buyholding():
    con = sqlite3.connect('./chronicle.db')
    cur = con.cursor()
    parsed_token = request.headers.get('Authorization')
    if parsed_token is None:
        raise InvalidUsage('Invalid Auth Token', status_code=403)
    data = request.get_json()
    portfolio_id = data['portfolio_id'],
    ticker = data['ticker'],
    avg_price  = data['avg_price'],
    quantity = data['quantity']

    cur.execute(f"select token from portfolio  where portfolio_id = '{portfolio_id}'")
    x = cur.fetchone()
    if x is None:
        raise InvalidUsage('Invalid Token', status_code=403)

    if isinstance(portfolio_id,int) is False and isinstance(quantity,int) is False and isinstance(avg_price,float) is False:
        raise InvalidUsage('Malformed Request', status_code=400)
    if  ticker.isalpha() is False:
        raise InvalidUsage('Malformed Request', status_code=400)

    cur.execute(f'select portfolio_id from portfolio where token = {parsed_token}')
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
    cur.execute(f'select ticker from stock where portfolio_id = {portfolio_id}')
    x = cur.fetchall()
    ticker_found = 0
    for sid in x:
        if ticker == sid[0]:
            ticker_found = 1
            break

    if quantity <= 0:
        raise InvalidUsage('Invalid quantity', status_code=404)
    if avg_price <= 0:
        raise InvalidUsage('Invalid price', status_code=404)

    # deduct from balance
    cur.execute(f'select balance from portfolio where token = {parsed_token} and portfolio_id = {portfolio_id}')
    balance = cur.fetchone()
    cash_amt = avg_price * quantity
    cash_amt = "{:.2f}".format(cash_amt)
    if cash_amt > balance:
        raise InvalidUsage('Not enough money in balance', status_code=404)
    cur.execute('BEGIN TRANSACTION;')
    query = f"""UPDATE portfolio p
                SET  p.balance = '{balance[0] - cash_amt}',
                WHERE p.portfolio_id = {portfolio_id};"""
    cur.execute(query)
    cur.execute('COMMIT;')

    # if not owned add to portfolio
    if ticker_found != 0:
        company = get_quote_data('nflx')['longName']
        cur.execute('BEGIN TRANSACTION;')
        query = f"""INSERT INTO stock (portfolio_id, ticker, company, avg_price, units)
                    VALUES ({portfolio_id}, '{ticker}', '{company}', {avg_price}, {quantity});"""
        cur.execute(query)
        cur.execute('COMMIT;')
    else:
        # if owned, update units and avg price
        cur.execute(f"select avg_price, units from stock where portfolio_id = {portfolio_id} and ticker = '{ticker}'")
        x = cur.fetchone()
        old_avg_price, old_units = x
        new_avg_price = ((old_avg_price[0] * old_units[0]) + (avg_price * quantity))/(quantity + old_units[0])
        new_avg_price = "{:.2f}".format(new_avg_price)
        cur.execute('BEGIN TRANSACTION;')
        query = f"""UPDATE stock
                    SET  avg_price = {new_avg_price},
                         units = {old_units[0] + quantity}
                    WHERE p.token = {parsed_token} and p.portfolio_id = {portfolio_id};"""
        cur.execute(query)
        cur.execute('COMMIT;')



    return {}

@app.route('/portfolio/sellholding')
@cross_origin()
def portfolio_sellholding():
    con = sqlite3.connect('./chronicle.db')
    cur = con.cursor()
    parsed_token = request.headers.get('Authorization')
    if parsed_token is None:
        raise InvalidUsage('Invalid Auth Token', status_code=403)
    data = request.get_json()
    portfolio_id = data['portfolio_id'],
    ticker = data['ticker'],
    avg_price  = data['avg_price'],
    quantity = data['quantity']

    cur.execute(f"select token from portfolio  where portfolio_id = '{portfolio_id}'")
    x = cur.fetchone()
    if x is None:
        raise InvalidUsage('Invalid Token', status_code=403)

    if isinstance(portfolio_id,int) is False and isinstance(quantity,int) is False and isinstance(avg_price,float) is False:
        raise InvalidUsage('Malformed Request', status_code=403)
    if  ticker.isalpha() is False:
        raise InvalidUsage('Malformed Request', status_code=403)

    cur.execute(f'select portfolio_id from portfolio where token = {parsed_token}')
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
    cur.execute(f'select ticker from stock where portfolio_id = {portfolio_id}')
    x = cur.fetchall()
    ticker_found = 0
    for sid in x:
        if ticker == sid[0]:
            ticker_found = 1
            break
    # if not owned raise error
    if ticker_found != 0:
        raise InvalidUsage('Stoct not owned', status_code=404)

    cur.execute(f"select units from stock where portfolio_id = {portfolio_id} and ticker = '{ticker}'")
    x = cur.fetchone()
    old_units = x

    if old_units[0] == quantity:
        query = f"""DELETE FROM stock
                        WHERE portfolio_id = {portfolio_id}
                        and ticker = '{ticker}';"""
        cur.execute(query)
    elif quantity > old_units[0]:
        raise InvalidUsage('Insufficient shares owned', status_code=400)
    else:
        # update units
        cur.execute(f"select units from stock where portfolio_id = {portfolio_id} and ticker = '{ticker}'")
        x = cur.fetchone()
        old_units = x
        cur.execute('BEGIN TRANSACTION;')
        query = f"""UPDATE stock
                    SET  units = {old_units[0] - quantity}
                    WHERE p.portfolio_id = {portfolio_id};"""
        cur.execute(query)
        cur.execute('COMMIT;')

    # add to balance
    cur.execute(f'select balance from portfolio where token = {parsed_token} and portfolio_id = {portfolio_id}')
    balance = cur.fetchone()
    cash_amt = avg_price * quantity
    cash_amt = "{:.2f}".format(cash_amt)
    cur.execute('BEGIN TRANSACTION;')
    query = f"""UPDATE portfolio p
                SET  p.balance = '{balance[0] + cash_amt}',
                WHERE p.token = {parsed_token} and p.portfolio_id = {portfolio_id};"""
    cur.execute(query)
    cur.execute('COMMIT;')

    return {}

@app.route('/portfolio/deleteholding')
@cross_origin()
def portfolio_deleteholding():
    con = sqlite3.connect('./chronicle.db')
    cur = con.cursor()
    parsed_token = request.headers.get('Authorization')
    if parsed_token is None:
        raise InvalidUsage('Invalid Auth Token', status_code=403)
    data = request.get_json()
    portfolio_id = data['portfolio_id'],
    ticker = data['ticker'],
    avg_price  = data['avg_price'],
    quantity = data['quantity']

    cur.execute(f"select token from portfolio  where portfolio_id = '{portfolio_id}'")
    x = cur.fetchone()
    if x is None:
        raise InvalidUsage('Invalid Token', status_code=403)

    if isinstance(portfolio_id,int) is False and isinstance(quantity,int) is False and isinstance(avg_price,float) is False:
        raise InvalidUsage('Malformed Request', status_code=403)
    if  ticker.isalpha() is False:
        raise InvalidUsage('Malformed Request', status_code=403)

    cur.execute(f'select portfolio_id from portfolio where token = {parsed_token}')
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
    cur.execute(f'select ticker from stock where portfolio_id = {portfolio_id}')
    x = cur.fetchall()
    ticker_found = 0
    for sid in x:
        if ticker == sid[0]:
            ticker_found = 1
            break
    # if not owned raise error
    if ticker_found != 0:
        raise InvalidUsage('Stoct not owned', status_code=404)

    query = f"""DELETE FROM stock
                    WHERE portfolio_id = {portfolio_id}
                    and ticker = '{ticker}';"""
    cur.execute(query)

    return {}

@app.route('/portfolio/holdings')
@cross_origin()
def portfolio_holdings():
    con = sqlite3.connect('./chronicle.db')
    cur = con.cursor()
    parsed_token = request.headers.get('Authorization')
    parsed_pid = request.headers.get('Query')
    if parsed_token is None:
        raise InvalidUsage('Invalid Auth Token', status_code=403)
    cur.execute(f"select token from portfolio  where portfolio_id = '{parsed_pid}'")
    x = cur.fetchone()
    if x is None:
        raise InvalidUsage('Invalid Token', status_code=403)
    cur.execute(f'select portfolio_id from portfolio where token = {parsed_token}')
    portfolio_found = 0
    x = cur.fetchall()
    for pid in x:
        if parsed_pid == pid[0]:
            portfolio_found = 1
            break
    if portfolio_found == 0:
        raise InvalidUsage('Portfolio not found', status_code=404)

    cur.execute(f"select ticker, company, avg_price, units from stock  where portfolio_id = '{parsed_pid}'")
    x = cur.fetchone()

    stock_list = []

    assets = 0
    for stock in x:
        ticker, company, avg_price, units = stock
        live_price = get_live_price(f'{ticker}')
        value = units[0] * live_price
        assets += value

    for holding in x:
        ticker, company, avg_price, units = holding
        temp = get_quote_data(f'{ticker[0]}')
        live_price = get_live_price(f'{ticker[0]}')
        change_p = temp['regularMarketChangePercent']
        change_p = "{:.5f}".format(change_p)
        change_d = temp['regularMarketChange']
        change_d = "{:.5f}".format(change_d)
        change = f'{change_d} ({change_p}%)'
        value = live_price * units[0]
        profit_loss_d = value - (units[0] * avg_price[0])
        if profit_loss_d > 0:
            profit_loss_p = profit_loss_d/value
        else:
            profit_loss_p = -1 * (100 - profit_loss_d/value)
        profit_loss_p = "{:.2f}".format(profit_loss_p)
        profit_loss_d = "{:.2f}".format(profit_loss_d)
        profit_loss = f'{profit_loss_d} ({profit_loss_p}%)'
        change_value = change_d * units[0]
        weight = value/assets * 100
        weight = "{:.2f}".format(weight)

        stock = {
            'ticker' : ticker[0],
            'company' : company[0],
            'live_price' : live_price,
            'change' : change,

            'profit_loss' : profit_loss,
            'units' : units[0],
            'avg_price' : avg_price[0],
            'value' : value,
            'weight' : weight,
            'change_value' : change_value
        }
        stock_list.append(stock)

    return stock_list



# @app.route('/user/list')
# @cross_origin()
# def user_list():
# con = sqlite3.connect('./chronicle.db')
# cur = con.cursor()


if __name__ == '__main__':
    app.run(debug=True, port=4500)