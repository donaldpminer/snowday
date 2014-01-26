from flask import Flask, session, redirect, url_for, escape, request, render_template, Markup
from redis import StrictRedis
from datetime import datetime

app = Flask(__name__)
app.debug = True

def get_redis(host='localhost', port=6379):
    return StrictRedis(host, port)

def header_string():
    if 'username' in session:
        return '''
Logged in as <b>%s</b> <a href='/logout'>Log Out</a>
<hr>
''' % escape(session['username'])
    else:
        return '''
<a href='/login'>Login</a>
<hr>

'''

def today():
    return str(datetime.now().date())

def right_now():
    return str(datetime.now())[:-10]

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'GET':
        return render_template('index.html', \
                checkins=xlist_todays_checkins(), \
                employees=get_employees())

    elif request.method == 'POST':
        redis = get_redis()

        if request.form['name'] == 'Select Employee...':
            return redirect(url_for('index'))

        if not redis.sismember('employees', request.form['name']):
            return "ERROR %s employee does not exists" % request.form['name']

        redis.hset('checkins', request.form['name'][:30].replace('|', '').strip(), \
            '%s|%s|%s|%s' % ( \
                request.form['time'][:30].replace('|', '').strip(), \
                request.form['comments'][:200].replace('|', '').strip(), \
                session['username'], \
                str(right_now())))

        return redirect(url_for('index'))


def xlist_todays_checkins():
    redis = get_redis()

    out = []

    for emp in get_employees():
        result = redis.hget('checkins', emp)

        if result is None:
            out.append(tuple([emp] + ['','','','']))
        else:
            out.append(tuple([emp] + result.split('|')))

    return out

@app.route('/list', methods=['GET', 'POST'])
def employeelist():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'GET':
        return render_template('list.html', emps=get_employees())

    elif request.method == 'POST':
        # the user tried to remove someone
        if 'removename' in request.form:
            get_redis().srem('employees', request.form['removename'])

        # the user tried to add someone
        elif 'name' in request.form:
            get_redis().sadd('employees', request.form['name'][:30].replace('|', ''))

        return redirect(url_for('employeelist'))

def get_employees():
    return sorted(get_redis().smembers('employees'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['username'] = request.form['username'].replace('|')
        return redirect(url_for('index'))
    return '''
        <form action="" method="post">
            <p><input type=text name=username> User Name</input></p>
            <p><input type=submit value=Login></input></p>
        </form>
    '''

@app.route('/logout')
def logout():
    # remove the username from the session if it's there
    session.pop('username', None)
    return redirect(url_for('index'))

# set the secret key.  keep this really secret:
app.secret_key = 'testicles123'

app.run()
