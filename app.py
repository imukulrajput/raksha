import os
import requests
from datetime import datetime
from flask import Flask, Response
from flask import request
import struct
import json
import logging
from pbparser.history_parser import ProceedHistoryData
from pbparser.oldman_parser import ProceedOldMan
from pbparser.alarm_parser import ProceedAlarmV2
from iutils.datetime_utils import is_valid_date
from iutils.datetime_utils import get_previous_day
from calculation.sleep_preprocessor import PrepareSleepData
from calculation.ecg_preprocessor import PrepareEcgData
from calculation.af_preprocessor import PrepareRriData
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
app = Flask(__name__)
 
@app.route("/pb/upload",methods=['POST']) 
def uploadPBData():
    payload = b''
    if request.content_type == 'application/x-www-form-urlencoded':
        payload = request.get_data()
    else:
        payload = request.data
    print(payload.hex())
    if len(payload) < 23:
        print('data length below 23')
        return Response(response=bytes([0x02]), status=200, mimetype="text/plain")
    device_bytes = bytearray(15)
    prefix_bytes = bytearray(2)
    len_bytes = bytearray(2)
    crc_bytes = bytearray(2)
    opt_bytes = bytearray(2)
    device_bytes[:15] = payload[:15]
    deviceid = device_bytes.decode()
    print('device: {0}'.format(deviceid))
    start_pos = 15
    while True:
        if len(payload)<start_pos+8:
            print('data length below {0}'.format(start_pos+8))
            return Response(response=bytes([0x02]), status=200, mimetype="text/plain")
        prefix_bytes[:2] = payload[start_pos:start_pos+2]
        if prefix_bytes[0] != 0x44 or prefix_bytes[1] != 0x54:
            print('invalid data header at {0}'.format(start_pos))
            return Response(response=bytes([0x03]), status=200, mimetype="text/plain")
        len_bytes[:2] = payload[start_pos+2:start_pos+4]
        length = int(len_bytes[1])*0x100 + int(len_bytes[0])
        crc_bytes[:2] = payload[start_pos+4:start_pos+6]
        opt_bytes[:2] = payload[start_pos+6:start_pos+8]
        if len(payload) < start_pos+8+length:
            print('data length below {0}'.format(start_pos+8+length))
            return Response(response=bytes([0x02]), status=200, mimetype="text/plain")
        pbPayload = payload[start_pos+8 : start_pos+8+length]
        opt = struct.unpack('<H', opt_bytes)[0]
        if opt == 0x0A:
            ProceedOldMan(pbPayload)
        elif opt == 0x80:

            data_dir = os.path.join(os.getcwd(), "raw_data")
            os.makedirs(data_dir, exist_ok=True)
            today_str = datetime.utcnow().strftime('%Y%m%d')
            filename = os.path.join(data_dir, f"{deviceid}_{today_str}_0x80.bin")
            with open(filename, "ab") as f:
                full_packet_data = payload[start_pos : start_pos+8+length]
                f.write(full_packet_data)

            ProceedHistoryData(pbPayload)
            PrepareSleepData(pbPayload)
            PrepareEcgData(pbPayload)
            PrepareRriData(pbPayload)
        start_pos += 8 + length
        if len(payload) == start_pos:
            #just read to the end and no extra byte leave
            break
    return Response(response=bytes([0x00]), status=200, mimetype="text/plain")



@app.route("/alarm/upload",methods=['POST'])
def uploadAlarmData():
    payload = b''
    if request.content_type == 'application/x-www-form-urlencoded':
        payload = request.get_data()
    else:
        payload = request.data
    print(payload.hex())
    if len(payload) < 23:
        print('data length below 23')
        return Response(response=bytes([0x02]), status=200, mimetype="text/plain")
    device_bytes = bytearray(15)
    prefix_bytes = bytearray(2)
    len_bytes = bytearray(2)
    crc_bytes = bytearray(2)
    opt_bytes = bytearray(2)     
    device_bytes[:15] = payload[:15]
    deviceid = device_bytes.decode()
    print('device: {0}'.format(deviceid))
    start_pos = 15
    while True:
        if len(payload)<start_pos+8:
            print('data length below {0}'.format(start_pos+8))
            return Response(response=bytes([0x02]), status=200, mimetype="text/plain")
        prefix_bytes[:2] = payload[start_pos:start_pos+2]
        if prefix_bytes[0] != 0x44 or prefix_bytes[1] != 0x54:
            print('invalid data header at {0}'.format(start_pos))
            return Response(response=bytes([0x03]), status=200, mimetype="text/plain")
        len_bytes[:2] = payload[start_pos+2:start_pos+4]
        length = int(len_bytes[1])*0x100 + int(len_bytes[0])
        crc_bytes[:2] = payload[start_pos+4:start_pos+6]
        opt_bytes[:2] = payload[start_pos+6:start_pos+8]
        if len(payload) < start_pos+8+length:
            print('data length below {0}'.format(start_pos+8+length))
            return Response(response=bytes([0x02]), status=200, mimetype="text/plain")
        pbPayload = payload[start_pos+8 : start_pos+8+length]
        opt = struct.unpack('<H', opt_bytes)[0]
        if opt == 0x12:
            ProceedAlarmV2(pbPayload)
        start_pos += 8 + length
        if len(payload) == start_pos:
            #just read to the end and no extra byte leave
            break
    return Response(response=bytes([0x00]), status=200, mimetype="text/plain")

@app.route("/call_log/upload",methods=['POST'])
def uploadCallLog():
    payload = b''
    call_log = {}
    if request.content_type == 'application/x-www-form-urlencoded':
        payload = request.get_data()
    else:
        payload = request.data
    resp = {}
    try:
        call_log = json.loads(payload)
        json_string = json.dumps(call_log, indent=4)
        print('call log: '+json_string)
        resp["ReturnCode"] = 0
    except json.JSONDecodeError:
        resp["ReturnCode"] = 10002
        
    return json.dumps(resp,ensure_ascii=False)

@app.route("/deviceinfo/upload",methods=['POST'])
def uploadDeviceInfo():
    payload = b''
    device_info = {}
    if request.content_type == 'application/x-www-form-urlencoded':
        payload = request.get_data()
    else:
        payload = request.data
    resp = {}
    try:
        device_info = json.loads(payload)
        json_string = json.dumps(device_info, indent=4)
        print('device info: '+json_string)
        resp["ReturnCode"] = 0
    except json.JSONDecodeError:
        resp["ReturnCode"] = 10002
        
    return json.dumps(resp,ensure_ascii=False)

@app.route("/status/notify",methods=['POST'])
def deviceStatusChange():
    payload = b''
    notify_info = {}
    if request.content_type == 'application/x-www-form-urlencoded':
        payload = request.get_data()
    else:
        payload = request.data
    resp = {}
    try:
        notify_info = json.loads(payload)
        json_string = json.dumps(notify_info, indent=4)
        print('device status change: '+json_string)
        resp["ReturnCode"] = 0
    except json.JSONDecodeError:
        resp["ReturnCode"] = 10002
        
    return json.dumps(resp,ensure_ascii=False)

@app.route("/")
def hello_world():
    return "hello world"


def read_and_process_raw_file(file_path):
    sleep_data_list = []
    rri_data_list = []

    if not os.path.exists(file_path):
        return sleep_data_list, rri_data_list
    
    with open(file_path, "rb") as f:
        payload = f.read()

    start_pos = 0
    while True:
        if len(payload) < start_pos + 8:
            break

        prefix_bytes = payload[start_pos:start_pos+2]
        if prefix_bytes != b'\x44\x54':
            logging.warning(f"Invalid packet header in file {file_path}")
            break

        len_bytes = payload[start_pos+2:start_pos+4]
        length = int(len_bytes[1])*0x100 + int(len_bytes[0])
        opt_bytes = payload[start_pos+6:start_pos+8]
        opt = struct.unpack('<H', opt_bytes)[0]

        if len(payload) < start_pos + 8 + length:
            break

        pbPayload = payload[start_pos+8 : start_pos+8+length]

        if opt == 0x80:     
            try:
                sleep_dict = PrepareSleepData(pbPayload) 
                rri_list = PrepareRriData(pbPayload)

                if sleep_dict:
                    sleep_data_list.append(sleep_dict)

                if rri_list: 
                    rri_data_list.extend(rri_list)

            except Exception as e:
                logging.error(f"Error processing packet in raw file: {e}")


        start_pos += 8 + length 
        if len(payload) == start_pos:       
            break 

    return sleep_data_list, rri_data_list

@app.route("/health/sleep", methods=['GET'])
def getSleepResult():     
    resp = {}     
    deviceid = request.args['deviceid']
    sleep_date = request.args['sleep_date']

    logging.info(f"Received /health/sleep request for Device ID: {deviceid} on Date: {sleep_date}") 

    if not deviceid or not sleep_date or not is_valid_date(sleep_date):
        resp["ReturnCode"] = 10002
        return json.dumps(resp,ensure_ascii=False)
    print(f"getSleepResult {deviceid} {sleep_date}")
    

    try:
        prev_day_str = get_previous_day(sleep_date).replace("-", "")
        prev_day_file = os.path.join(os.getcwd(), "raw_data", f"{deviceid}_{prev_day_str}_0x80.bin")
        prevDay_list, prevDayRri_list = read_and_process_raw_file(prev_day_file)

        current_day_str = sleep_date.replace("-", "")
        current_day_file = os.path.join(os.getcwd(), "raw_data", f"{deviceid}_{current_day_str}_0x80.bin")
        nextDay_list, nextDayRri_list = read_and_process_raw_file(current_day_file)

        if not prevDay_list and not nextDay_list:
            logging.warning(f"No raw data found for {deviceid} on {sleep_date}")
            resp["ReturnCode"] = 10404  
            return json.dumps(resp, ensure_ascii=False)
        

        algo_payload = {
            "prevDay": json.dumps(prevDay_list),
            "nextDay": json.dumps(nextDay_list),
            "prevDayRri": prevDayRri_list,
            "nextDayRri": nextDayRri_list,
            "recordDate": int(current_day_str),
            "device_id": deviceid,
            "account": "iwown",
            "password": "iwown2013"
        }

        api_url = "https://iwap1.iwown.com/algoservice/calculation/sleep"
        api_response = requests.post(api_url, json=algo_payload, timeout=90)
        api_response.raise_for_status()  

        logging.info("Successfully received real sleep data from Algorithm API") 

        return api_response.json()
    
    except requests.exceptions.RequestException as e:
        logging.error(f"Algorithm API call failed: {e}")
        resp["ReturnCode"] = 10505 
        return json.dumps(resp, ensure_ascii=False)  
    except Exception as e:
        logging.error(f"An error occurred during sleep calculation: {e}", exc_info=True)
        resp["ReturnCode"] = 10001
        return json.dumps(resp, ensure_ascii=False)

if __name__ == '__main__':
    app.run(port=8098)    
  