
import sGUI.timers as timers
from sGUI.FT8_tcvr import config

class IcomCIV:
    import serial

    def __init__(self):
        self.serial_port = False
        try:
            self.serial_port = self.serial.Serial(port = config.COM_port, baudrate = config.baudrate, timeout = 0.1)
            if (self.serial_port):
                timers.timedLog(f"Connected to {config.COM_port}")
        except IOError:
            timers.timedLog(f"Couldn't connect to {config.COM_port} - running without CI-V")

    def decode_twoBytes(self, twoBytes):
        if(len(twoBytes)==2):
            n1 = int(twoBytes[0])
            n2 = int(twoBytes[1])
            return  n1*100 + (n2//16)*10 + n2 %16
        
    def sendCAT(self, cmd):
        if(not self.serial_port): return
        self.serial_port.reset_input_buffer()
        msg = b'\xfe\xfe\x88\xe0' + cmd + b'\xfd'
        timers.timedLog(f"[CAT] send {msg.hex(' ')}")
        self.serial_port.write(msg)
        resp = self.serial_port.read_until(b'\xfd')
        resp = self.serial_port.read_until(b'\xfd')
        timers.timedLog(f"[CAT] response {resp.hex(' ')}")
        return resp

    def setFreqHz(self, freqHz):
        s = f"{freqHz:09d}"
        timers.timedLog(f"[CAT] SET frequency")
        timers.timedLog(f"[CAT] {s}")
        fBytes = b"".join(bytes([b]) for b in [16*int(s[7])+int(s[8]),16*int(s[5])+int(s[6]),16*int(s[3])+int(s[4]),16*int(s[1])+int(s[2]), int(s[0])])
        self.sendCAT(b"".join([b'\x00', fBytes]))

    def setMode(self, md='USB', dat=False, filIdx = 1 ):
        timers.timedLog(f"[CAT] SET mode: {md} data:{dat} filter:{filIdx}")
        mdIdx = ['LSB','USB','AM','CW','RTTY','FM','WFM','CW-R','RTTY-R'].index(md)
        datIdx = 1 if dat else 0
        self.sendCAT(b''.join([b'\x26\x00', bytes([mdIdx]), bytes([datIdx]), bytes([filIdx]) ]) )

    def setPTTON(self):
        timers.timedLog(f"[CAT] PTT On")
        self.sendCAT(config.PTT_on)

    def setPTTOFF(self):
        timers.timedLog(f"[CAT] PTT Off")
        self.sendCAT(config.PTT_off)

    def getSWR(self):
        resp = False
        self.setMode("RTTY")
        self.setPTTON()
        timers.sleep(0.05)
        timers.timedLog(f"CAT command: get SWR")
        resp = self.sendCAT(b'\x15\x12')
        self.setPTTOFF()
        self.setMode(md="USB", dat = True, filIdx = 1)
        resp_decoded = self.decode_twoBytes(resp[-3:-1])
        if(resp_decoded):
            return int(resp_decoded)

    def getPWR(self):
        resp = False
        timers.timedLog(f"CAT command: get PWR")
        resp = self.sendCAT(b'\x14\x0A')
        resp_decoded = self.decode_twoBytes(resp[-3:-1])
        if(resp_decoded):
            return int(resp_decoded)
       
      

#====================================================
# Not used in sGUI
#====================================================

    def getFreqHz(self):
        while self.serial_port.read():
            pass
        timers.timedLog(f"CAT command: get frequency")
        self.sendCAT(b'\x03')
        if(not self.serial_port): return
        resp = self.serial_port.read_until()
        timers.timedLog(f"CAT: Icom responded with {resp}")
        if(len(resp)<10):
            return False
        return int("".join(f"{(b >> 4) & 0x0F}{b & 0x0F}" for b in reversed(resp[11:16])))

