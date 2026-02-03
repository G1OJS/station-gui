
from sGUI.comms_hub import start_UI, send_to_ui_ws
import threading
import sGUI.timers as timers
from sGUI.IcomCIV import IcomCIV
from sGUI.antennas import AntennaControl
from sGUI.FT8_tcvr import ReceiveFT8, FT8_QSO, config


def onMagloopStatus(status):
    send_to_ui_ws("antenna_control", {'MagloopStatus':f"{status}"})
    
def onMagloopStep(step):
    send_to_ui_ws("antenna_control", {'MagloopStep':f"{step}"})

def query_loop():
    antenna_control.send_command('<Q>')

def poll_rig():
    while True:
        timers.sleep(2)
        band_power = 100 if config.myFreq < 100 else 50 if config.myFreq < 200 else 35
        p = rig.getPWR()
        if(p):
            p = band_power * p / 255.0
            send_to_ui_ws("rig_status", {"PowerLevel":f"{p:3.0f}W"})
        query_loop()

def check_swr():
    s = rig.getSWR()
    if(s):
        send_to_ui_ws("rig_status", {"swr":f"{s:3.0f}"})

def harmonise_calls(call):
    if("<" in call):
        call = "HASHED"
    return call

def onDecode(decode_dict):
    msg_parts = decode_dict['msg'].split()
    call_a, call_b, grid_rpt = msg_parts[0], msg_parts[1], msg_parts[2]  
    if(call_a == config.myCall or call_b == config.myCall or 'rxfreq' in decode_dict or decode_dict['f']==config.rxfreq or call_b==QSO.their_call):
        decode_dict.update({'priority':True})
    decode_dict.update({'f':str(int(decode_dict['f']))})
    decode_dict.update({'call_a':harmonise_calls(call_a)})
    decode_dict.update({'call_b':harmonise_calls(call_b)})
    decode_dict.update({'grid_rpt':grid_rpt})
    decode_dict.update({'cyclestart_str':decode_dict['cs']})

    send_to_ui_ws("decode_dict", decode_dict)
    if (call_a == config.myCall and call_b == QSO.their_call):
        QSO.progress(decode_dict)

def process_UI_event(event):
    topic = event['topic']
    print(f"[sGUI] process_ui_event {topic}")
    if(topic in ["ui.clicked-message", "ui.repeat-last", "ui.call-cq"]):
        QSO.process_UI_event(event)
    if("set-band" in topic):
        set_band_freq(topic)
    if(topic=="ui.check-swr"):
        check_swr()
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
    threading.Thread(target = poll_rig, daemon = True).start()

rig = IcomCIV()
antenna_control = AntennaControl(onMagloopStatus, onMagloopStep)
rxFT8 = ReceiveFT8(onDecode)
QSO = FT8_QSO(rig)

run()
    
