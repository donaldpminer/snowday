from flask import Flask, session, redirect, url_for, escape, request, render_template, Markup
from redis import StrictRedis
from datetime import datetime
import json
import time

app = Flask(__name__)
app.debug = True
app.secret_key = 'i guess i should figure out a way to make this more secure'

# HELPER FUNCTIONS

# returns an active client to the redis instance
def get_redis(host='localhost', port=6379):
    return StrictRedis(host, port)

# returns the timestamp of right now
def right_now():
    return int(time.time())

# get a list of employees
def get_employees():
    return sorted(get_redis().smembers('employees'))

# produces a json string from a series of items
def gen_checkin_json(name='', timein='', comments='', author='', time=''):
    obj = {'name' : str(name), \
           'timein' : str(timein), \
           'comments': str(comments), \
           'author': str(author), \
           'time': int(time) }

    return json.dumps(obj)

# returns a list of json docs of the checkins from today

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


# MAIN PAGES

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'username' not in session:
        return redirect(url_for('login'))

    # this happens when someone is just checking out the index page
    if request.method == 'GET':
        return render_template('index.html', \
                checkins=list_todays_checkins(), \
                employees=get_employees())

    # this happens when someone is trying to checkin
    elif request.method == 'POST':
        redis = get_redis()

        # this means they didn't select an employee
        if request.form['name'] == 'Select Employee...':
            return redirect(url_for('index'))

        if not redis.sismember('employees', request.form['name']):
            # this should never happen
            return "ERROR %s employee does not exists" % request.form['name']

        # ok, we're good to go
        redis.lpush('ci:%s' % request.form['name'], \
            gen_checkin_json(\
                request.form['name'], \
                request.form['time'][:30].strip(), \
                request.form['comments'][:200].strip(), \
                session['username'], \
                str(right_now())))

        return redirect(url_for('index'))

# this page shows information about a user
@app.route('/user/<user>', methods=['GET'])
def userpage(user):
    if 'username' not in session:
        return redirect(url_for('login'))

    # convert each checkin from a json string into a dict
    checkins = [ json.loads(ci) for ci in get_redis().lrange('ci:%s' % user, 0, -1) ]

    # this goes through and changes timestamps to time strings
    #   can this be done in javascript?
    for ci in checkins:
        ci['time'] = str(datetime.fromtimestamp(int(ci['time'])))
    
    return render_template('userpage.html', checkins=checkins, username=user)


@app.route('/list', methods=['GET', 'POST'])
def employeelist():
    if 'username' not in session:
        return redirect(url_for('login'))

    # this happens when someone is just visiting the employee list
    if request.method == 'GET':
        return render_template('list.html', emps=get_employees())

    # this happens when someone tried to do something on the employee list
    elif request.method == 'POST':
        # the user tried to remove someone
        if 'removename' in request.form:
            r = get_redis()
            r.srem('employees', request.form['removename'])
            r.delete('ci:%s' % request.form['removename'])

        # the user tried to add someone
        elif 'name' in request.form:
            get_redis().sadd('employees', request.form['name'][:30].replace('|', ''))

        return redirect(url_for('employeelist'))



# APIs FOR ACCESSING DATA
#    these just return json

@app.route('/raw/user/<user>.json', methods=['GET'])
def raw_checkin(user):
    if 'username' not in session:
        return 'you are not logged in'

    # convert each checkin into python, then convert the whole thing back into json
    return json.dumps([ json.loads(ci) for ci in get_redis().lrange('ci:%s' % user, 0, -1) ])

@app.route('/raw/employeelist.json', methods=['GET'])
def raw_employeelist():
    if 'username' not in session:
        return 'you are not logged in'

    return json.dumps(get_employees())


# LOGIN AND SESSION STUFF

@app.route('/login', methods=['GET', 'POST'])
def login():

    # this user is trying to login
    if request.method == 'POST':
        un = request.form['username']

        # if this is a good login
        if get_redis().sismember('employees', un) or un == 'admin':
            session['username'] = un
            return redirect(url_for('index'))

        # if this is a bad login
        else:
            return render_template('login.html', error_message='user "%s" doesn\'t exist' % un)

    # this user is trying to see the login page
    return render_template('login.html')

@app.route('/logout')
def logout():
    # remove the username from the session if it's there
    session.pop('username', None)
    return redirect(url_for('index'))


# START SERVER
if __name__ == "__main__":
    app.run()


