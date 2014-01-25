from flask import Flask, session, redirect, url_for, escape, request
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
    return str(datetime.now())


@app.route('/', methods=['GET', 'POST'])
def index():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'GET':
        return header_string() + '''
        <form action="" method="post">
            <p><input type=text name=name> Name of employee</input</p>
            <p><input type=text name=time> Time coming in</input></p>
            <p><input type=text name=comments> Comments</input</p>
            <p><input type=submit value=Post>
        </form>
''' + list_todays_checkins()
    elif request.method == 'POST':
        get_redis().lpush('ci-%s' % today(), \
            '%s|%s|%s|%s|%s' % ( \
                request.form['name'][:30], \
                request.form['time'][:30], \
                request.form['comments'][:200], \
                session['username'], \
                str(right_now())))

        return redirect(url_for('index'))

def list_todays_checkins():
    checkins = get_redis().lrange('ci-%s' % today(), 0, -1)
    out_str = '''
        <table border=1 cellpadding=4>
            <tr><td>Employee Name</td><td>Time Coming In</td><td>Comments</td><td>Author</td><td>Check-in Time</td></tr>
'''
    for checkin in checkins:
        out_str += '<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % tuple(checkin.split('|'))

    out_str += '</table>'

    return out_str


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['username'] = request.form['username']
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
