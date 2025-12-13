
from sGUI.wsjtx import start_wsjtx_tailer
from sGUI.comms_hub import config, start_UI, send_to_ui_ws
import threading
from sGUI.IcomCIV import IcomCIV
from sGUI.antennas import AntennaControl
antenna_control = AntennaControl()
rig = IcomCIV()

def process_UI_event(event):
    import sGUI.timers as timers
    from sGUI.comms_hub import send_to_ui_ws
    global QSO
    topic = event['topic']
    if(topic == "ui.clicked-message"):
        from sGUI.comms_hub import send_to_ui_ws
        selected_message = event
        timers.timedLog(f"[process_UI_event] Clicked on message {selected_message}")
        config.txfreq = config.clearest_txfreq
        config.rxfreq = int(selected_message['freq'])
        timers.timedLog(f"[process_UI_event] Set Rx freq to {config.rxfreq}", logfile = 'QSO.progress.log')
        QSO.tx_cycle = QSO.tx_cycle_from_clicked_message(selected_message)
        selected_message.update({'priority':True})
        send_to_ui_ws("decode_dict", selected_message)
        if(selected_message['call_a'] == "CQ" or selected_message['call_a'] == config.myCall):
            QSO.progress(selected_message)
    if(topic == "ui.repeat-last"):
        QSO.rpt_cnt = 0
        QSO.progress({"repeat_tx":True})
    if(topic == "ui.call-cq"):
        QSO.clear()
        t = timers.tnow()
        i = int(((t-2) % 30)/15) 
        QSO.tx_cycle = ['odd','even'][i]
        QSO.transmit(f"CQ {config.myCall} {config.mySquare}")
    if("set-band" in topic):
        set_band_freq(topic)
    if(topic=="ui.check-swr"):
        rig.setMode("RTTY")
        rig.setPTTON()
        timers.sleep(0.5)
        rig.setPTTOFF()
        timers.sleep(0.5)
        rig.setMode(md="USB", dat = True, filIdx = 1)
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
    start_wsjtx_tailer(onDecode)
    
run()
    
