from flask import Flask, session, redirect, url_for, escape, request, render_template, Markup
from redis import StrictRedis
from datetime import datetime
import json
import time

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
    return int(time.time())

def ts2datestr(ts):
    return datetime.fromtimestamp(ts)

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'GET':
        return render_template('index.html', \
                checkins=list_todays_checkins(), \
                employees=get_employees())

    elif request.method == 'POST':
        redis = get_redis()

        if request.form['name'] == 'Select Employee...':
            return redirect(url_for('index'))

        if not redis.sismember('employees', request.form['name']):
            # this should never happen
            return "ERROR %s employee does not exists" % request.form['name']

        redis.lpush('ci:%s' % request.form['name'], \
            gen_checkin_json(\
                request.form['name'], \
                request.form['time'][:30].strip(), \
                request.form['comments'][:200].strip(), \
                session['username'], \
                str(right_now())))

        return redirect(url_for('index'))

def gen_checkin_json(name='', timein='', comments='', author='', time=''):
    obj = {'name' : str(name), \
           'timein' : str(timein), \
           'comments': str(comments), \
           'author': str(author), \
           'time': int(time) }

    return json.dumps(obj)

def list_todays_checkins():
    redis = get_redis()

    out = []

    for emp in get_employees():
        # get the first element from ci:<username>, which is the most recent one
        result = redis.lindex('ci:%s' % emp, 0)

        if result is None:
            out.append({'name' : emp, 'time' : 'NONE EVER'})
        else:
            obj = json.loads(result)

            # if the status was less than a day ago
            # (1 day = 86400 seconds)
            if time.time() - int(obj['time']) <= 86400:
                # change it from time stamp to readable string
                obj['time'] = str(datetime.fromtimestamp(int(obj['time'])))

                out.append(obj)
            else:
                out.append({'name' : emp, 'time': 'NONE TODAY'})

    return out

@app.route('/user/<user>', methods=['GET'])
def userpage(user):
    if 'username' not in session:
        return redirect(url_for('login'))

    checkins = [ json.loads(ci) for ci in get_redis().lrange('ci:%s' % user, 0, -1) ]
    for ci in checkins:
        ci['time'] = str(datetime.fromtimestamp(int(ci['time'])))
    
    return render_template('userpage.html', checkins=checkins, username=user)

@app.route('/raw/status/<user>.json', methods=['GET'])
def raw_checkin(user):
    if 'username' not in session:
        return 'you are not logged in'

    return get_redis().hget('checkins', user)

@app.route('/raw/employeelist.json', methods=['GET'])
def raw_employeelist():
    if 'username' not in session:
        return 'you are not logged in'

    return json.dumps(get_employees())

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
        un = request.form['username']
        if get_redis().sismember('employees', un) or un == 'admin':
            session['username'] = un
            return redirect(url_for('index'))
        else:
            return '''
        <p>Member <b>%s</b> does not exist. Try again</p>

        <form action="" method="post">
            <p><input type=text name=username> User Name</input></p>
            <p><input type=submit value=Login></input></p>
        </form>
    ''' % un
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
