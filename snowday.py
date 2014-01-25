from flask import Flask, request


app = Flask(__name__)
app.debug = True

@app.route('/bob/<bob>')
def hello_world(bob):
    return 'hello world bitches and ' + str(bob)

@app.route('/edit', methods=['POST', 'GET'])
def note():
    name = request.args.get('name', '')
    time = request.args.get('time', '')
    message = request.args.get('message', '')

    return str(name) + str(time) + str(message)

if __name__ == '__main__':
    app.run()
