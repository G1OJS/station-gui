
from sGUI.comms_hub import config, start_UI, send_to_ui_ws
import threading
import time
from sGUI.IcomCIV import IcomCIV
from sGUI.antennas import AntennaControl
from sGUI.FT8_tcvr import ReceiveFT8, FT8_QSO

def check_rig():
    while True:
        time.sleep(2)
        band_power = 100 if config.myFreq < 100 else 50 if config.myFreq < 200 else 35
        p = band_power * rig.getPWR() / 255.0
        send_to_ui_ws("rig_status", {"PowerLevel":f"{p:3.0f}W"})

def onDecode(decode_dict):
    import sGUI.timers as timers
    from sGUI.comms_hub import config, send_to_ui_ws
    if(decode_dict['call_a'] == config.myCall or decode_dict['call_b'] == config.myCall or 'rxfreq' in decode_dict or decode_dict['freq']==config.rxfreq or decode_dict['call_b']==QSO.their_call):
        decode_dict.update({'priority':True})
    send_to_ui_ws("decode_dict", decode_dict)
    if (decode_dict['call_a'] == config.myCall and decode_dict['call_b'] == QSO.their_call):
        QSO.progress(decode_dict)

def onOccupancy(spectrum_occupancy, spectrum_df, f0=0, f1=3500, bin_hz=10):
    from sGUI.comms_hub import config, send_to_ui_ws
    import sGUI.timers as timers
    import numpy as np

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
    
    config.update_clearest_txfreq(clear_freq)
    timers.timedLog(f"[onOccupancy] occupancy data received, set Tx to {config.txfreq}")
    send_to_ui_ws("freq_occ_array", {'histogram':occupancy.tolist()})

def process_UI_event(event):
    import sGUI.timers as timers
    from sGUI.comms_hub import send_to_ui_ws
    global QSO
    topic = event['topic']
    print(f"[sGUI] process_ui_event {topic}")
    if(topic in ["ui.clicked-message", "ui.repeat-last", "ui.call-cq"]):
        QSO.process_UI_event(event)
    if("set-band" in topic):
        set_band_freq(topic)
    if(topic=="ui.check-swr"):
        print(rig.getSWR())
    if(topic=="ui.magloop-nudge-up"):
        antenna_control.send_command("<NU>");
    if(topic=="ui.magloop-nudge-down"):
        antenna_control.send_command("<ND>");
        
def set_band_freq(action):
    # action = set-band-name-freq or set-band-name
    fields = action.split("-")
    config.myBand = fields[2]
    if(len(fields)==4):
        config.myFreq = float(fields[3])
    if(len(fields)==3):
        config.myFreq = float(list(filter(lambda b: b['band_name'] == config.myBand, config.bands))[0]['band_freq'])
    rig.setFreqHz(int(config.myFreq * 1000000))
    rig.setMode(md="USB", dat = True, filIdx = 1)
    bandconfig = list(filter(lambda b: b['band_name'] == config.myBand, config.bands))[0]
    rx_ant, tx_ant = bandconfig['rx_ant'].lower(), bandconfig['tx_ant'].lower()
    for ant in config.antennas:
        if(ant['ant_name'] == rx_ant): antenna_control.send_command(ant['serCmd'])
        if(ant['ant_name'] == tx_ant): antenna_control.send_command(ant['serCmd'])
    with open("sGUI_MHz.txt","w") as f:
        f.write(str(config.myFreq))
    send_to_ui_ws("set_band", {"band":config.myBand})

def add_action_buttons():
    from sGUI.comms_hub import config, send_to_ui_ws
    send_to_ui_ws("add_action_button", {'caption':'Call CQ', 'action':'call-cq', 'class':'button transmitting_button'})
    send_to_ui_ws("add_action_button", {'caption':'Repeat last', 'action':'repeat-last', 'class':'button transmitting_button'})
    send_to_ui_ws("add_action_button", {'caption':'Check SWR', 'action':'check-swr', 'class':'button transmitting_button'})
    send_to_ui_ws("add_action_button", {'caption':'Loop Up', 'action':'magloop-nudge-up', 'class':'button transmitting_button'})
    send_to_ui_ws("add_action_button", {'caption':'Loop Down', 'action':'magloop-nudge-down', 'class':'button transmitting_button'})
    for band in config.bands:
        send_to_ui_ws("add_action_button", {'caption':band['band_name'], 'action':f"set-band-{band['band_name']}-{band['band_freq']}", 'class':'button'})
    
def run():        
    start_UI("sGUI.html", process_UI_event)
    add_action_buttons()
    send_to_ui_ws("set_myCall", {'myCall':config.myCall})
    send_to_ui_ws("set_mySquare", {'mySquare':config.mySquare})
    send_to_ui_ws("connect_pskr_mqtt", {'dummy':'dummy'})
    set_band_freq(f"set-band-{config.myBand}")
    threading.Thread(target = check_rig, daemon = True).start()

rig = IcomCIV()
antenna_control = AntennaControl(rig)
rxFT8 = ReceiveFT8(onDecode)
QSO = FT8_QSO(rig)

run()
    
