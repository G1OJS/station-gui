import numpy as np
import threading
import time
import pickle
import matplotlib.pyplot as plt
import time, queue
from matplotlib import rcParams
from matplotlib.widgets import Slider, Button
from matplotlib.animation import FuncAnimation


class Rig:

    def __init__(self, verbose = False, port = 'COM4', baudrate = 9600):
        import serial
        self.serial = serial
        self.serial_port = False
        self.port = port
        self.baudrate = baudrate
        self.verbose = verbose
 
    def vprint(self, text):
        if self.verbose:
            print(text)

    def _decode_twoBytes(self, twoBytes):
        if(len(twoBytes)==2):
            n1 = int(twoBytes[0])
            n2 = int(twoBytes[1])
            return  n1*100 + (n2//16)*10 + n2 %16
        
    def _sendCAT(self, cmd):
        try:
            self.serial_port = self.serial.Serial(port = self.port, baudrate = self.baudrate, timeout = 0.1)
            self.serial_port.reset_input_buffer()
            msg = b'\xfe\xfe\x88\xe0' + cmd + b'\xfd'
            self.vprint(f"[CAT] send {msg.hex(' ')}")
            self.serial_port.write(msg)
            resp = self.serial_port.read_until(b'\xfd')
            resp = self.serial_port.read_until(b'\xfd')
            self.vprint(f"[CAT] response {resp.hex(' ')}")
            self.serial_port.close()
            return resp
        except:
            print(f"couldn't send command {msg.hex(' ')}")
            time.sleep(0.1)
        return ''

    def set_freq_Hz(self, freqHz):
        s = f"{freqHz:09d}"
        self.vprint(f"[CAT] SET frequency")
        self.vprint(f"[CAT] {s}")
        fBytes = b"".join(bytes([b]) for b in [16*int(s[7])+int(s[8]),16*int(s[5])+int(s[6]),16*int(s[3])+int(s[4]),16*int(s[1])+int(s[2]), int(s[0])])
        self._sendCAT(b"".join([b'\x00', fBytes]))

    def get_freq_Hz(self):
        self.vprint(f"CAT command: get frequency")
        resp = self._sendCAT(b'\x03')
        self.vprint(f"CAT: Icom responded with {resp}")
        if(len(resp)>10):
            return int("".join(f"{(b >> 4) & 0x0F}{b & 0x0F}" for b in reversed(resp[5:10])))

    def ptt_on(self, PTT_on = b'\x1c\x00\x01'):
        self.vprint(f"[CAT] PTT On")
        self._sendCAT(PTT_on)

    def ptt_off(self, PTT_off = b'\x1c\x00\x00'):
        self.vprint(f"[CAT] PTT Off")
        self._sendCAT(PTT_off)

    def setMode(self, md='USB', dat=False, filIdx = 1 ):
        self.vprint(f"[CAT] SET mode: {md} data:{dat} filter:{filIdx}")
        mdIdx = ['LSB','USB','AM','CW','RTTY','FM','WFM','CW-R','RTTY-R'].index(md)
        datIdx = 1 if dat else 0
        self._sendCAT(b''.join([b'\x26\x00', bytes([mdIdx]), bytes([datIdx]), bytes([filIdx]) ]) )

    def getSWR(self):
        resp = False
        self.setMode("RTTY")
        self.setPWR(10)
        self.ptt_on()
        time.sleep(0.01)
        self.vprint(f"CAT command: get SWR")
        resp = self._sendCAT(b'\x15\x12')
        self.ptt_off()
        self.setMode(md="USB", dat = True, filIdx = 1)
        resp_decoded = self._decode_twoBytes(resp[-3:-1])
        if(resp_decoded):
            return 1 + 2*resp_decoded/255

    def setPWR(self, pwr):
        self.vprint(f"CAT command: set PWR")
        resp = self._sendCAT(b'\x14\x0A\x00\x28')

    def getPWR(self):
        resp = False
        self.vprint(f"CAT command: get PWR")
        resp = self._sendCAT(b'\x14\x0A')
        resp_decoded = self._decode_twoBytes(resp[-3:-1])
        if(resp_decoded):
            return int(resp_decoded)

class Arduino:
    def __init__(self, verbose = False, port = 'COM7', baudrate = 9600):
        import serial
        self.serial = serial
        self.serial_port = False
        self.port = port
        self.baudrate = baudrate
        self.verbose = verbose
        self.loop_step = 500
        self.ready = False
        self.bands = {'160m': (1.8, 2.0), '80m':  (3.5, 3.8), '60m':  (5.25, 5.45),
                 '40m':  (7.0, 7.2), '30m':  (10.1, 10.15), '20m':  (14.0, 14.35),
                 '17m':  (18.068, 18.168),'15m':  (21.0, 21.45),'12m':  (24.89, 24.99),
                 '10m':  (28.0, 29.7), '6m':   (50.0, 52.0), '2m': (144.0, 146.0)}
        self.default_search = {'bands':['160m', '80m', '60m', '40m'],
                        'steps': [ [58.5, 59, 59.5, 60, 60.5, 61], np.arange(300,320,5), np.arange(597,608,1), np.arange(870,895,2)]}
        self.load_tunings()
        self.connect()

    def band_from_freq(self, fMHz):
        for band, (lo, hi) in self.bands.items():
            if lo <= fMHz <= hi:
                return band

    def connect(self):
        try:
            self.serial_port = self.serial.Serial(port = self.port, baudrate = self.baudrate, timeout = 0.1)
            if (self.serial_port):
                self.vprint(f"Connected to {self.port}")
        except IOError:
            self.vprint(f"Couldn't connect to {self.port}")

    def monitor(self):
        while True:
            time.sleep(0.05)
            d = self.serial_port.readline().decode('UTF-8')
            print(d)
            if 'CurrStep' in d:
                self.loop_step = int(d[9:])
            if 'READY' in d:
                self.ready = True
                break
            
    def send_command(self, c):
        self.ready = False
        self.vprint(f"[ARD] send {c}")
        self.serial_port.write(c.encode('UTF-8'))

    def load_tunings(self):
        try:
            with open('loop.pkl', 'rb') as f:
                self.good_tunings = pickle.load(f)
            print(self.good_tunings)
        except:
            self.good_tunings = {}
            self.save_tunings()

    def update_tunings(self, fkHz, step):
        if not fkHz in self.good_tunings:
            self.good_tunings[fkHz] = 0
        self.good_tunings[fkHz] = step
        self.save_tunings()

    def save_tunings(self):
        with open('loop.pkl', 'wb') as f:
            pickle.dump(self.good_tunings, f)
        
    def get_tuning(self, fkHz):
        if fkHz in self.good_tunings:
            s = self.good_tunings[fkHz]
            return [s-1, s, s+1]
        else:
            band = self.band_from_freq(fkHz/1000)
            if band in self.default_search['bands']:
                idx = self.default_search['bands'].index(band)
                return self.default_search['steps'][idx]

    def move_to(self, step):
        self.send_command(f"<T{step}>")

    def vprint(self, text):
        if self.verbose:
            print(text)
      
class Gui:
    def __init__(self, on_control_click):
        self.on_control_click = on_control_click
        self.pmarg = 0.04
        self.pos_slider_target = None
        self.swr_slider_target = None
        self.make_layout()
        self.anim = FuncAnimation(self.fig, self._animate, interval=100)

    def make_layout(self, wf_left = 0.15, wf_top = 0.87):
        rcParams['toolbar'] = 'None'
        self.plt = plt
        self.fig = plt.figure(figsize = (4,4), facecolor=(.18, .71, .71, 0.4)) 
        self.fig.canvas.manager.set_window_title('Antcontrol by G1OJS')

        styles = {'ctrl':{'fc':'grey','c':'black'}, 'band':{'fc':'green','c':'white'}}
        button_defs = [ {'label':'Tune loop', 'style':'ctrl', 'data':''},
                        {'label':'Check swr', 'style':'ctrl', 'data':''},
                        {'label':'Main = Loop', 'style':'ctrl', 'data':''},
                        {'label':'Main = Dipoles', 'style':'ctrl', 'data':''},
                        {'label':'Rx on main', 'style':'ctrl', 'data':''},
                        {'label':'Rx on alt', 'style':'ctrl', 'data':''}]
        self._make_buttons(button_defs, styles, wf_top, 0.06, 0.8, 0.01)

        ax_swr_slider = self.fig.add_axes([0.2,0.2, 0.6, 0.05])
        self.swr_slider = Slider(ax_swr_slider,  'SWR', 1, 3, orientation='horizontal', dragging = False)
        ax_pos_slider = self.fig.add_axes([0.2,0.1, 0.6, 0.05])
        self.pos_slider = Slider(ax_pos_slider,  'Step', 30, 900, orientation='horizontal', dragging = False)

    def _make_buttons(self, buttons, styles, btns_top, btn_h, btn_w, sep_h):
        self.buttons = []
        for i, btn in enumerate(buttons):
            btn_axs = plt.axes([0.5*(1-btn_w), btns_top - (i+1) * btn_h, btn_w, btn_h-sep_h])
            style = styles[btn['style']]
            btn_widg = Button(btn_axs, btn['label'], color=style['fc'], hovercolor='skyblue')
            btn_widg.data = btn['data']
            btn_widg.on_clicked(lambda event, btn_widg=btn_widg: self.on_control_click(btn_widg))
            self.buttons.append(btn_widg)
        
    def _animate(self, frame):
        if self.pos_slider_target is not None:
            self.pos_slider.set_val(self.pos_slider_target)
            self.pos_slider_target = None
        if self.swr_slider_target is not None:
            self.swr_slider.set_val(self.swr_slider_target)
            self.swr_slider_target = None
        return []

    def config_for_band(self, band):
        print(f"Configure for {band}")
        if band in ['160m','80m','60m','40m']:
            self.send_command("<RM>")
            self.send_command("<ML>")
        else:
            self.send_command("<RA>")
            self.send_command("<MD>")

class App:
      
    def __init__(self):
        self.current_kHz = 0
        self.rig = Rig(verbose = False)
        self.ard = Arduino(verbose = True)
        self.gui = Gui(self.on_control_click)
        threading.Thread(target = self.ard.monitor, daemon = True).start()
        self.gui.plt.show()

    def check_swr(self):
        s = self.rig.getSWR()
        self.gui.swr_slider_target = s
        return s

    def tune_loop(self):
        self.ard.send_command("<ML>")
        fkHz = self.rig.get_freq_Hz()/1000
        steps = self.ard.get_tuning(fkHz)
        if steps is not None:
            for step in steps:
                self.ard.move_to(step)
                while not self.ard.ready:
                    self.gui.pos_slider_target = self.ard.loop_step
                    time.sleep(0.001)
                self.gui.pos_slider_target = self.ard.loop_step
                s = self.check_swr()
                if s is not None:
                    if s < 100:
                        self.ard.update_tunings(fkHz, step)
                        return

    def on_control_click(self, btn_widg):
        data = btn_widg.data
        txt = btn_widg.label.get_text()
        if txt == 'Check swr':
            self.check_swr()
        if txt == 'Main = Loop':
            self.ard.send_command("<ML>")
        if txt == 'Main = Dipoles':
            self.ard.send_command("<MD>")
        if txt == 'Rx on main':
            self.ard.send_command("<RM>")
        if txt == 'Rx on alt':
            self.ard.send_command("<RA>")
        if txt == 'Tune loop':
            if txt == 'Tune loop':
                threading.Thread(target=self.tune_loop, daemon=True).start()
           

app = App()

