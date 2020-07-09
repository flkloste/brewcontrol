from flask import Flask, render_template, redirect, url_for,request
from flask import make_response
from flask import send_from_directory
import hold_temp_module as htmod
import threading
import csv
import StringIO
import os

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
        self.ht.setSollTemp(soll_temp)

    def set_hysterese(self, hysterese):
        self.ht.setHysterese(hysterese)

    def get_temp(self):
        return self.ht.getIstTempString()

    def get_info(self):
        return self.ht.getInfoStats()
        
    def get_csv_as_list(self):
        return self.ht.getCsv()


dir_path = os.path.dirname(os.path.realpath(__file__))
app = Flask(__name__, template_folder=dir_path)
app._static_folder = dir_path
handler = Handler()

@app.route('/')
@app.route("/index")
def server_index():
    return render_template('index.html')

@app.route('/data.csv')
@app.route('/test.csv')
def server_return_csv():
#    with handler.csvLock:
#        return send_from_directory('/home/pi/python-server-brew-control/', 'test.csv', cache_timeout=1)
    csv = StringIO.StringIO()
    csv.write("Zeit,Ist,Soll,Freq\n");
    for row in handler.get_csv_as_list():
        csv.write(row)
    
    output = make_response(csv.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=export.csv"
    output.headers["Content-type"] = "text/csv"
    return output

def server_download_csv():
    with handler.csvLock:
        return send_from_directory('/home/pi/python-server-brew-control/', 'test.csv', cache_timeout=1, as_attachment=True)

@app.route('/neu', methods=['GET', 'POST'])
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

@app.route('/set_hysterese', methods=['GET', 'POST'])
def server_set_hysterese():
    if request.method == 'POST':
        datafromjs = request.form['mydata']
        if htmod.isInt(datafromjs):
            datafromjs = int(datafromjs)
        if htmod.isInt(datafromjs) and datafromjs >= 0 and datafromjs < 300:
            handler.set_hysterese(datafromjs)
        else:
            print "falsche inegabe\n"

        resp = make_response('{"response": "ok"}')
        resp.headers['Content-Type'] = "application/json"
        return resp

@app.route('/start', methods=['GET', 'POST'])
def server_start():
    if request.method == 'POST':
        handler.start()
        resp = make_response('{"response": "ok"}')
        resp.headers['Content-Type'] = "application/json"
        return resp

@app.route('/stop', methods=['GET', 'POST'])
def server_stop():
    if request.method == 'POST':
        handler.stop()
        resp = make_response('{"response": "ok"}')
        resp.headers['Content-Type'] = "application/json"
        return resp

@app.route('/get_temp', methods=['GET', 'POST'])
def server_get_temp():
    if request.method == 'POST':
        temp = handler.get_temp()
        resp = make_response('{"response": '+temp+'}')
        resp.headers['Content-Type'] = "application/json"
        return resp

@app.route('/get_info', methods=['GET', 'POST'])
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
        json_string = '{"mode": "'+ mode +'", "soll": "' + info.soll_temp + '", "ist": "' + info.ist_temp +'", "running": "' + is_running + '", "power": "' + power_status + '", "hysterese": "' + info.hysterese + '"}'
        # print json_string
        resp = make_response(json_string)
        resp.headers['Content-Type'] = "application/json"
        return resp


if __name__ == "__main__":
    app.run(host='0.0.0.0', threaded=True)
