from flask import Flask, render_template, redirect, url_for,request
from flask import make_response
from functools import wraps
from flask import request, Response
#from flask import send_from_directory
import hold_temp_module as htmod
import threading
import StringIO


########################
## Hold Temp Handler ###
########################

class Handler:
    def __init__(self):
        self.csvLock = threading.Lock()
        self.ht = htmod.HoldTemp(htmod.MODE.HEAT, 20, 0, self.csvLock)
        self.ht.daemon = True
        self.ht.start()
        self.status = 0    

    def neu(self, in_mode):
        self.ht.stop()

        mode = ''
        if(in_mode == 'h'):
            mode = htmod.MODE.HEAT
        elif(in_mode == 'f'):
            mode = htmod.MODE.COOL
        else:
            raise ValueError("Error: Unknown mode")
        self.ht = htmod.HoldTemp(mode, 20, 0, self.csvLock)
        self.ht.daemon = True
        self.ht.start()

    def start(self):
        self.status = 1
        self.ht.startControl()

    def stop(self):
        self.status = 0
        self.ht.stopControl()

    def set_temp(self, soll_temp):
#        print "handler set_temp %s\n" % soll_temp
        self.ht.setSollTemp(soll_temp)

    def get_temp(self):
        return self.ht.getIstTempString()

    def get_info(self):
        return self.ht.getInfoStats()
        
    def get_csv_as_list(self):
        return self.ht.getCsv()



app = Flask(__name__, template_folder='/home/pi/python-server-brew-control/')
app._static_folder = '/home/pi/python-server-brew-control/'
handler = Handler()


########################
##### Basic Auth #######
########################

def check_auth(in_username, in_password):
    """This function is called to check if a username /
    password combination is valid.
    """
    try:
        with open("credo", "r") as f:
            username = ""
            password = ""
            for line in f:
                m = re.match(r"^user=([^\n\r]+)", line)
                if m:
                    username = m.group(1)
                m = re.match(r"^pw=([^\n\r]+)", line)
                if m:
                    password = m.group(1)
            if username not "" and password not "":
                return username == in_username and password == in_password
    
    except:
        pass
    
    return False
        
    

def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
    'Could not verify your access level for that URL.\n'
    'You have to login with proper credentials', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

    
########################
#### HTML Requests #####
########################

@app.route('/')
@app.route("/index")
@requires_auth
def server_index():
    return render_template('index.html')

@app.route('/data.csv')
@app.route('/test.csv')
@requires_auth
def server_return_csv():
#    with handler.csvLock:
#        return send_from_directory('/home/pi/python-server-brew-control/', 'test.csv', cache_timeout=1)
    csv = StringIO.StringIO()
    csv.write("Zeit,Ist,Soll\n");
    for row in handler.get_csv_as_list():
        csv.write(row)
    
    output = make_response(csv.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=export.csv"
    output.headers["Content-type"] = "text/csv"
    return output

#def server_download_csv():
#    with handler.csvLock:
#        return send_from_directory('/home/pi/python-server-brew-control/', 'test.csv', cache_timeout=1, as_attachment=True)

@app.route('/neu', methods=['GET', 'POST'])
@requires_auth
def server_neu():
    if request.method == 'POST':
        mode = request.form['mode']
        if mode == 'h':
            handler.neu('h')
        elif mode == 'f':
            handler.neu('f')
        resp = make_response('{"response": "ok"}')
        resp.headers['Content-Type'] = "application/json"
        return resp

@app.route('/set_temp', methods=['GET', 'POST'])
@requires_auth
def server_set_temp():
    if request.method == 'POST':
        datafromjs = request.form['mydata']
        if htmod.isInt(datafromjs):
            datafromjs = int(datafromjs)
        if htmod.isInt(datafromjs) and datafromjs >= 0 and datafromjs < 100:
            handler.set_temp(datafromjs)
        else:
            print "falsche inegabe\n"

        resp = make_response('{"response": "ok"}')
        resp.headers['Content-Type'] = "application/json"
        return resp

@app.route('/start', methods=['GET', 'POST'])
@requires_auth
def server_start():
    if request.method == 'POST':
        handler.start()
        resp = make_response('{"response": "ok"}')
        resp.headers['Content-Type'] = "application/json"
        return resp

@app.route('/stop', methods=['GET', 'POST'])
@requires_auth
def server_stop():
    if request.method == 'POST':
        handler.stop()
        resp = make_response('{"response": "ok"}')
        resp.headers['Content-Type'] = "application/json"
        return resp

@app.route('/get_temp', methods=['GET', 'POST'])
@requires_auth
def server_get_temp():
    if request.method == 'POST':
        temp = handler.get_temp()
        resp = make_response('{"response": '+temp+'}')
        resp.headers['Content-Type'] = "application/json"
        return resp

@app.route('/get_info', methods=['GET', 'POST'])
@requires_auth
def server_get_info():
    if request.method == 'POST':
        info = handler.get_info()
        mode = ''
        if info.mode == htmod.MODE.HEAT:
            mode = 'Heizen'
        else:
            mode = 'Kuehlen'
        is_running = ''
        if info.is_running == 1:
            is_running = 'aktiv'
        else:
            is_running = 'gestoppt'
        power_status = ''
        if info.power_status == 'on':
            power_status = 'Strom an'
        else:
            power_status = 'Strom aus'
        json_string = '{"mode": "'+ mode +'", "soll": "' + info.soll_temp + '", "ist": "' + info.ist_temp +'", "running": "' + is_running + '", "power": "' + power_status + '"}'
        # print json_string
        resp = make_response(json_string)
        resp.headers['Content-Type'] = "application/json"
        return resp


if __name__ == "__main__":
    app.run(host='0.0.0.0', threaded=True)
