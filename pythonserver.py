from flask import Flask, render_template, redirect, url_for,request
from flask import make_response
from flask import send_from_directory
import hold_temp_module as htmod
import threading

class Handler:
	def __init__(self):
		self.ht = htmod.HoldTemp(htmod.MODE.HEATING, 20, 0)
		self.ht.daemon = True
		self.ht.start()
		self.status = 0

	def neu(self, in_mode):
		self.ht.stop()

		mode = ''
		if(in_mode == 'h'):
			mode = htmod.MODE.HEATING
		elif(in_mode == 'f'):
			mode = htmod.MODE.FREEZING
		else:
			raise ValueError("Error: Unknown mode")
		self.ht = htmod.HoldTemp(mode, 20, 0)
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

	def get_temp(self):
		return self.ht.getIstTemp()
	
	def get_info(self):
		return self.ht.getInfoStats()



app = Flask(__name__, template_folder='/home/pi/python-server-brew-control/')
app._static_folder = '/home/pi/python-server-brew-control/'
handler = Handler()

@app.route('/')
@app.route("/index")
def server_index():
    return render_template('index.html')

@app.route('/test.csv')
def server_return_csv():
    return send_from_directory('/home/pi/python-server-brew-control/', 'test.csv')

@app.route('/neu', methods=['GET', 'POST'])
def server_neu():
    if request.method == 'POST':
        datafromjs = request.form['mydata']
	handler.neu('h')
        resp = make_response('{"response": "ok"}')
        resp.headers['Content-Type'] = "application/json"
        return resp

@app.route('/set_temp', methods=['GET', 'POST'])
def server_set_temp():
   if request.method == 'POST':
        datafromjs = request.form['mydata']
	handler.set_temp(datafromjs)
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
	if info.mode == htmod.MODE.HEATING:
		mode = 'Heizen' 
	else:
		mode = 'Kuehlen'
	is_running = ''
	if info.is_running == 1:
		is_running = 'aktiv'
	else:
		is_running = 'idle'
	power_status = ''
	if info.power_status == 1:
		power_status = 'Strom an'
	else:
		power_status = 'Strom aus'
	json_string = '{"mode": "'+ mode +'", "soll": "' + info.soll_temp + '", "ist": "' + info.ist_temp +'", "running": "' + is_running + '", "power": "' + power_status + '"}'
	print json_string 
	resp = make_response(json_string)
	resp.headers['Content-Type'] = "application/json"
	return resp






if __name__ == "__main__":
	app.run(host='0.0.0.0') 