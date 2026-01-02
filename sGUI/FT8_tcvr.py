import numpy as np
import os
import threading
import sGUI.timers as timers
from sGUI.comms_hub import send_to_ui_ws

import sys
sys.path.append(r"C:\Users\drala\Documents\Projects\GitHub\PyFT8")
import PyFT8.FT8_encoder as FT8_encoder
import PyFT8.audio as audio
from PyFT8.cycle_manager import Cycle_manager
from PyFT8.sigspecs import FT8
import sGUI.logging as logging

import configparser
class Config:
    def __init__(self):
        self.txfreq = 1000
        self.txfreq = 1000
        self.rxfreq = 1000
        self.bands = []
        self.antennas = []
        self.myBand = "20m"
        self.myFreq = False
        if(not self.check_config()):
            return
        parser = configparser.ConfigParser()
        parser.read("sGui.ini")
        self.input_device_keywords = parser.get("sound","soundcard_rx").split("_")
        self.output_device_keywords = parser.get("sound","soundcard_tx").split("_")
        self.myCall = parser.get("myStation","myCall")
        self.mySquare = parser.get("myStation","mySquare")
        self.myBand = parser.get("startup","myBand")
        self.wsjtx_all_file = parser.get("paths","wsjtx_all_file")

        self.COM_port = parser.get("radio","com_port")
        self.baudrate = parser.get("radio","baudrate")
        self.PTT_on = bytes.fromhex(parser.get("radio","ptt_on"))
        self.PTT_off = bytes.fromhex(parser.get("radio","ptt_off"))

        self.AC_port = parser.get("antenna_control","com_port")
        self.AC_baudrate = parser.get("antenna_control","baudrate")
        for ant_name, serCmd in parser.items("antennas"):
            self.antennas.append({"ant_name":ant_name, "serCmd":serCmd})

        for band_name, band_def in parser.items("bands"):
            band_config = band_def.split("-")
            self.bands.append({"band_name":band_name, "band_freq":band_config[0], "rx_ant":band_config[1],"tx_ant":band_config[2]})

    def check_config(self):
        if(os.path.exists("sGUI.ini")):
            return True
        else:
            print("[comms hub] No PyFT8.ini in current directory.")

    def update_txfreq(self, clear_freq):
        self.txfreq = clear_freq
        send_to_ui_ws("set_txfreq", {'freq':str(self.txfreq)})
    
config = Config()

class FT8_QSO:
    def __init__(self, rig):
        self.tx_cycle = False
        self.tx_msg = False
        self.rpt_cnt = 0
        self.my_snr = False
        self.their_grid = False
        self.their_call = False
        self.their_snr = False
        self.time_on = False
        self.time_off = False
        self.date = False
        self.date_off = False
        self.rig = rig
        self.output_device_idx = audio.find_device(config.output_device_keywords)
        self.audio_out = audio.AudioOut()

    def clear(self):
        self.cycle = 'next'
        self.tx_msg = False
        self.my_snr = False
        self.their_grid = False
        self.their_call = False
        self.time_on = False
        self.time_off = False
        self.date = False
        self.date_off = False

    def tx_cycle_from_clicked_message(self, selected_message):
        return 'odd' if (selected_message['cyclestart_str'][-2:] in ['00','30']) else 'even'

    def time_to_begin_tx(self, tnow, tx_cycle):
        max_immediate = 15 - 12.6
        t = tnow + (15 if tx_cycle == 'odd' else 0)
        t = t %30
        twait = 30 - t
        if(twait > 30-max_immediate): twait=0
        tbegin = twait + tnow
        import sGUI.timers as timers
        timers.timedLog(f"[QSO.transmit] time_to_begin_tx calculated {tbegin} with inputs {t}, {tx_cycle}", logfile = 'QSO.progress.log')
        return tbegin

    def wait_for_sec(self, sec):
        twait = sec - timers.tnow()
        if(twait > 0):
            timers.timedLog(f"[QSO.transmit] Waiting for {self.tx_cycle} cycle start ({twait:4.1f}s)", logfile = 'QSO.progress.log')
            timers.sleep(twait)

    def progress(self, msg_dict):
        # work out *what* to transmit. *when* is worked out in transmit below
        timers.timedLog(f"[QSO.progress] QSO.tx_cycle is {self.tx_cycle}", logfile = 'QSO.progress.log')
        if("repeat_tx" in msg_dict):
            if(self.tx_msg and self.tx_cycle):
                self.transmit(self.tx_msg)
            return

        call_a, their_call, grid_rpt = msg_dict['call_a'], msg_dict['call_b'], msg_dict['grid_rpt']
        if(call_a == "CQ" or call_a == config.myCall):
            self.their_call = their_call
            self.their_snr = int(msg_dict['snr'])
            self.date, self.time_on = timers.QSO_dnow_tnow()

        if("+" not in grid_rpt and "-" not in grid_rpt and "73" not in grid_rpt):
            self.their_grid = grid_rpt
            
        timers.timedLog(f"[QSO.progress] Progress QSO with {self.their_call}", logfile = 'QSO.progress.log')
        timers.timedLog(f"[QSO.progress] msg_dict = {msg_dict}", logfile = 'QSO.progress.log')
        if('73' in grid_rpt or 'R' in grid_rpt):
            reply = '73'
            if (grid_rpt[-4]=='R' and grid_rpt[-3] !='R'):
                reply = 'RR73'
            self.transmit(f"{self.their_call} {config.myCall} {reply}")
            self.date_off, self.time_off = timers.QSO_dnow_tnow()
            self.log()
            self.clear()
            return

        if(len(grid_rpt)>=3):
            if(grid_rpt[-3]=="+" or grid_rpt[-3]=="-"):
                self.transmit(f"{self.their_call} {config.myCall} R{self.their_snr:+03d}")
                self.my_snr = grid_rpt[-3:]
                return

        if(call_a == "CQ"):
            self.transmit(f"{self.their_call} {config.myCall} {config.mySquare}")
            return

        if(call_a == config.myCall):
            self.transmit(f"{self.their_call} {config.myCall} {self.their_snr:+03d}")
            return
        
    def transmit(self, tx_msg):
        self.rpt_cnt = self.rpt_cnt + 1 if(tx_msg == self.tx_msg ) else 0
        if(self.rpt_cnt >= 5):
            timers.timedLog("[QSO.transmit] Skip, repeat count too high", logfile = 'QSO.progress.log')
            return
        if(not tx_msg):
            timers.timedLog("[QSO.transmit] Skip, no message", logfile = 'QSO.progress.log')
            return
        self.tx_msg = tx_msg
        timers.timedLog(f"[QSO.transmit] Send message: ({self.rpt_cnt}) {tx_msg}", logfile = 'QSO.progress.log')
        tx_at_sec =  self.time_to_begin_tx(timers.tnow(), self.tx_cycle)
        c1, c2, grid_rpt = tx_msg.split()
        symbols = FT8_encoder.pack_message(c1, c2, grid_rpt)
        self.tx_ogm_to_priority_ui(c1, c2, grid_rpt, tx_at_sec)
        audio_data = self.audio_out.create_ft8_wave(symbols, f_base = config.txfreq)
        # doing tx threaded gives time for the tx_ogm to appear on the UI
        threading.Thread(target = self.do_tx, args=(audio_data, tx_at_sec, )).start()
            
    def do_tx(self, audio_data, tx_at_sec):
        self.wait_for_sec(tx_at_sec)
        timers.sleep(0.05)
        timers.timedLog(f"[QSO.transmit] PTT ON", logfile = 'QSO.progress.log')
        self.rig.setPTTON()
        self.audio_out.play_data_to_soundcard(audio_data, self.output_device_idx)
        self.rig.setPTTOFF()
        timers.timedLog(f"[QSO.transmit] PTT OFF", logfile = 'QSO.progress.log')

    def tx_ogm_to_priority_ui(self, c1, c2, grid_rpt, tx_at_sec):
        cycle_start_str = timers.strftime("%H%M%S", tx_at_sec);
        tx_ogm_dict = {'cyclestart_str':f"X_{cycle_start_str}", 'priority':True,
                    'snr':'-', 'freq':str(int(config.txfreq)), 'dt':' ',
                    'call_a':c1, 'call_b':c2, 'grid_rpt':grid_rpt}
        send_to_ui_ws("decode_dict", tx_ogm_dict)

    def log(self):
        log_dict = {'call':self.their_call, 'gridsquare':self.their_grid, 'mode':'FT8',
        'operator':config.myCall, 'station_callsign':config.myCall, 'my_gridsquare':config.mySquare, 
        'rst_sent':f"{int(self.their_snr):+03d}", 'rst_rcvd':f"{int(self.my_snr):+03d}", 
        'qso_date':self.date, 'time_on':self.time_on,
        'qso_date_off':self.date_off, 'time_off':self.time_off,
        'band':config.myBand, 'freq':config.myFreq, 'comment':'sGUI' }
        import sGUI.timers as timers
        timers.timedLog("[QSO.log] send to ADIF {log_dict}", logfile = 'QSO.progress.log')
        logging.append_qso("sGUI.adi", log_dict)

    def process_UI_event(self, event):
        topic = event['topic']
        print(f"[FT8_tcvr] process_ui_event {topic}")
        if(topic == "ui.clicked-message"):
            from sGUI.comms_hub import send_to_ui_ws
            selected_message = event
            timers.timedLog(f"[process_UI_event] Clicked on message {selected_message}")
            config.txfreq = config.txfreq
            config.rxfreq = int(selected_message['freq'])
            timers.timedLog(f"[process_UI_event] Set Rx freq to {config.rxfreq}", logfile = 'QSO.progress.log')
            self.tx_cycle = self.tx_cycle_from_clicked_message(selected_message)
            selected_message.update({'priority':True})
            send_to_ui_ws("decode_dict", selected_message)
            if(selected_message['call_a'] == "CQ" or selected_message['call_a'] == config.myCall):
                self.progress(selected_message)
        if(topic == "ui.repeat-last"):
            self.rpt_cnt = 0
            self.progress({"repeat_tx":True})
        if(topic == "ui.call-cq"):
            self.clear()
            t = timers.tnow()
            i = int(((t-2) % 30)/15) 
            self.tx_cycle = ['odd','even'][i]
            self.transmit(f"CQ {config.myCall} {config.mySquare}")

def onOccupancy(spectrum_occupancy, spectrum_df, f0=0, f1=3500, bin_hz=10):
    occupancy_fine = spectrum_occupancy/np.max(spectrum_occupancy)
    n_out = int((f1-f0)/bin_hz)
    occupancy = np.zeros(n_out)
    for i in range(n_out):
        occupancy[i] = occupancy_fine[int((f0+bin_hz*i)/spectrum_df)]
    fs0, fs1 = 1000,2000
    if(config.myBand == '60m'):
        fs0, fs1 = 400,990
    bin0 = int((fs0-f0)/bin_hz)
    bin1 = int((fs1-f0)/bin_hz)
    clear_freq = fs0 + bin_hz*np.argmin(occupancy[bin0:bin1])
    occupancy = 10*np.log10(occupancy + 1e-12)
    occupancy = 1 + np.clip(occupancy, -40, 0) / 40
    
    config.update_txfreq(clear_freq)
    timers.timedLog(f"[onOccupancy] occupancy data received, band is {config.myBand}, set Tx to {config.txfreq}")
    send_to_ui_ws("freq_occ_array", {'histogram':occupancy.tolist()})


class ReceiveFT8:
    def __init__(self, onDecode):
        self.onDecode = onDecode
        threading.Thread(target = self.wsjtx_all_tailer,
                         kwargs = ({'all_txt_path':config.wsjtx_all_file,
                                    'on_decode':onDecode})).start()
        cycle_manager = Cycle_manager(FT8, 
                          self.onDecodePyFT8, onOccupancy = onOccupancy,
                          input_device_keywords = config.input_device_keywords)

    def onDecodePyFT8(self, c):
        import time
        decode_dict = {'decoder':'PyFT8', 'cyclestart_str':c.cyclestart_str,
                   'call_a':c.call_a, 'call_b':c.call_b, 'grid_rpt':c.grid_rpt, 'freq':c.fHz,
                   't_decode':time.time(), 'snr':c.snr, 'dt':c.dt, 'sync_score':c.sync_score}
        self.onDecode(decode_dict)    

    def wsjtx_all_tailer(self, all_txt_path, on_decode):
        def follow():
            with open(all_txt_path, "r") as f:
                f.seek(0, 2)
                while True:
                    line = f.readline()
                    if not line:
                        timers.sleep(0.2)
                        continue
                    yield line.strip()
        for line in follow():
            ls = line.split()
            decode_dict = False
            try:
                decode_dict = {'decoder':'WSJTX', 'cyclestart_str':ls[0],'snr':ls[4], 'dt':ls[5], 'freq':ls[6], 'call_a':ls[7], 'call_b':ls[8], 'grid_rpt':ls[9]}
            except:
                pass
            if(decode_dict):
                decode_dict.update({'dedupe_key':ls[0]+" "+ ls[7]+" "+ ls[8] + " "+ls[9]})
                on_decode(decode_dict)
 
