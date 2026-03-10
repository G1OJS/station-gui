import numpy as np
import threading
import time

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

    def connect(self):
        try:
            self.serial_port = self.serial.Serial(port = self.port, baudrate = self.baudrate, timeout = 0.1)
            if (self.serial_port):
                self.vprint(f"Connected to {self.port}")
        except IOError:
            print(f"Couldn't connect to {self.port}")

    def _decode_twoBytes(self, twoBytes):
        if(len(twoBytes)==2):
            n1 = int(twoBytes[0])
            n2 = int(twoBytes[1])
            return  n1*100 + (n2//16)*10 + n2 %16
        
    def _sendCAT(self, cmd):
        self.connect()
        try:
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
            print("couldn't send command")
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
        time.sleep(0.05)
        self.vprint(f"CAT command: get SWR")
        resp = self._sendCAT(b'\x15\x12')
        self.ptt_off()
        self.setMode(md="USB", dat = True, filIdx = 1)
        resp_decoded = self._decode_twoBytes(resp[-3:-1])
        if(resp_decoded):
            return int(resp_decoded)

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
        self.connect()

    def vprint(self, text):
        if self.verbose:
            print(text)

    def connect(self):
        try:
            self.serial_port = self.serial.Serial(port = self.port, baudrate = self.baudrate, timeout = 0.1)
            if (self.serial_port):
                self.vprint(f"Connected to {self.port}")
        except IOError:
            print(f"Couldn't connect to {self.port}")
            
    def send_command(self, c):
        self.vprint(f"[ARD] send {c}")
        self.serial_port.write(c.encode('UTF-8'))

    def sleep_until(self, resp):
        while True:
            time.sleep(0.01)
            d = self.serial_port.readline().decode('UTF-8')
            #if(len(d)>5):
            #    self.vprint(f"[ARD] response {d}")
            if resp in d:
                break

bands = {
    '160m': (1.8, 2.0),
    '80m':  (3.5, 3.8),
    '60m':  (5.25, 5.45),
    '40m':  (7.0, 7.2),
    '30m':  (10.1, 10.15),
    '20m':  (14.0, 14.35),
    '17m':  (18.068, 18.168),
    '15m':  (21.0, 21.45),
    '12m':  (24.89, 24.99),
    '10m':  (28.0, 29.7),
    '6m':   (50.0, 52.0),
}

def tune(band):
    if band == '160m': steps = [58.5, 59, 59.5, 60, 60.5, 61]
    if band == '80m': steps = np.arange(300,320,5)
    if band == '60m': steps = np.arange(600,620,5)
    if band == '40m': steps = np.arange(865,890,5)
    s = rig.getSWR()
    if s < 100:
        return
    for t in steps:
        time.sleep(1)
        ard.send_command(f"<T{t}>")
        ard.sleep_until('TUNED')
        s = rig.getSWR()
        print(t,s)
        if s < 100:
            break

def band_from_freq(freq_Hz):
    freq_mHz = freq_Hz / 1000000.0
    for band, (lo, hi) in bands.items():
        if lo <= freq_mHz <= hi:
            return band
    return None
      
def setband(band):
    global current_band
    if band in ['160m','80m','60m','40m']:
        ard.send_command("<RM>")
        ard.send_command("<ML>")
        if band != current_band:
            tune(band)
        current_band = band
    else:
        ard.send_command("<RA>")
        ard.send_command("<MD>")

rig = Rig(verbose = False)
ard = Arduino(verbose = False)
ard.sleep_until('READY')
current_band = None
while True:
    time.sleep(0.1)
    f = rig.get_freq_Hz()
    band = band_from_freq(f)
    if band is not None:
        setband(band)

