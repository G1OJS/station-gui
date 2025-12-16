
import serial
from sGUI.FT8_tcvr import config
import sGUI.timers as timers
import threading
from sGUI.comms_hub import start_UI, send_to_ui_ws

class AntennaControl:
    
    def __init__(self, rig):
        timers.timedLog(f"[Antennas] Connecting to {config.AC_port}")
        self.arduino = False
        self.running = True
        self.rig = rig
        try:
            self.arduino = serial.Serial(config.AC_port, baudrate=config.AC_baudrate, timeout=0.1)
        except:
            pass
        if (self.arduino):
            timers.timedLog(f"[Antennas] Connected to {config.AC_port}")
            threading.Thread(target = self.monitor_arduino, daemon=True).start()

            
    def send_command(self, c):
        if c:
            if("<T" in c):
                timers.timedLog(f"[Antennas] Send 'TUNING' message to UI")
                send_to_ui_ws("antenna_control", {'MagloopTuning':'TUNING'})
            timers.timedLog(f"[Antennas] Send command {c}")
            self.arduino.write(c.encode('UTF-8'))

    def monitor_arduino(self):
        while self.running:
            while self.arduino.in_waiting == 0:
                timers.sleep(0.25)
            d = self.arduino.readline()
            if(b"TUNED" in d):
                timers.timedLog(f"[Antennas] Send 'TUNED' message to UI")
                send_to_ui_ws("antenna_control", {'MagloopTuning':'TUNED: CHECK SWR'})
                s = self.rig.getSWR()
                if(s):
                    if(s < 90):
                        send_to_ui_ws("antenna_control", {'MagloopTuning':'TUNED: SWR OK'})
