# main.py  
  
import argparse  
import os  
import re  
from pathlib import Path  
import sys
import my_module  
import draw
import getpass    
  

 
class UserInput:
    def __init__(self, phone_number,  log_path='.'):
        self.phone_number = phone_number
        self.log_path = log_path
        self.is_wav_file = phone_number.endswith('.wav')
        self.is_phone_number = phone_number.isdigit()

    def is_phone_number(self): 
        return self.is_phone_number 
    
    def is_wav_file(self):   
        return self.is_wav_file      
 
  
def is_log_file(s):  
    return s.endswith('.log') and (s.startswith('rec') or s.startswith('sbc'))  
  
def check_and_get_files(path, pattern):  
    if os.path.isfile(path):  
        if is_log_file(path):  
            return [path] if re.search(pattern, open(path, 'r').read()) else []  
        else:  
            raise ValueError(f"The second parameter is not a valid log file: {path}")  
    elif os.path.isdir(path):  
        valid_logs = [f for f in Path(path).glob('**/*.log') if is_log_file(f.name)]  
        return [log for log in valid_logs if re.search(pattern, open(log, 'r').read())]  
    else:  
        raise ValueError(f"The second parameter is not a valid file or directory: {path}")  
  
def find_call_records(log_files, phone_number):  
    matched_logs = []
    for file in log_files:
        with open(file, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
            for line in lines: 
                if phone_number in line:
                    matched_logs.append(file)
                    break
    return matched_logs
  
def get_rtp_stats(log_file, call_id):  
    # 假设这个函数会根据Call-ID检索RTP收发包统计  
    pass  
  
def save_sip_to_file(log_file, call_id, sip_file):  
    # 假设这个函数会保存SIP信息到sip.txt文件  
    pass  
  
def print_device_info(sip_info):  
    # 假设这个函数会打印设备名和地址  
    pass  

def delete_old_sip_file(filename='sip.txt'):
    # 检查文件是否存在  
    if os.path.exists(filename):  
        # 如果文件存在，则删除  
        os.remove(filename)  
        print(f"旧文件{filename} 已被删除") 

def main():
    current_user = getpass.getuser()  
    my_module.custom_log(my_module.A_VERY_LONG_LINE, my_module.logging.INFO)
    
    parser = argparse.ArgumentParser(description='[IPCC5.0通话记录分析程序]')  
    parser.add_argument('phone_or_wav', type=str, help='电话号码或录音文件名')  
    parser.add_argument('path_or_file', type=str, nargs='?', default='.', help='路径或文件名（可选，默认为当前工作目录）')  
    if len(sys.argv) < 2:
        parser.print_help() 
        return
    
    args = parser.parse_args()  
  
    userInput =UserInput(args.phone_or_wav,args.path_or_file)

    if not (userInput.is_phone_number or userInput.is_wav_file):
        raise ValueError('The first parameter is not a valid phone number or .wav file.')      
    
    log_files = []
    try:  
        if os.path.isdir(userInput.log_path):
            for root, dirs, files in os.walk(userInput.log_path):
                for file in files: 
                    if ('rec' in file or 'sbc' in file) and file.endswith('.log'):
                        filename = os.path.join(root, file)
                        log_files.append(filename)
            my_module.custom_log(f'遍历日志文件,{log_files}', my_module.logging.INFO)
        elif os.path.isfile(userInput.log_path):
            log_files.append(userInput.log_path)
            my_module.custom_log(f'独立日志文件,{userInput.log_path}', my_module.logging.INFO)
        else:
            raise ValueError('The second parameter is not a log path or  file.')  
    except ValueError as e:  
        print(e)  
        return  
     
    if len(log_files) == 0:  
        print(f"No log files found containing the pattern: {log_files}")  
        return  
  
    call_records = find_call_records(log_files, userInput.phone_number)  
    if not call_records:  
        my_module.custom_log(f"在提供的{log_files}日志中，查不到这个号码或录音{userInput.phone_number}",my_module.logging.FATAL)  
        return  
  
    selectItem = None
    try:
        call, call_legs = my_module.chooseOneCall(userInput.phone_number, log_files)
    except:
        print('error !')
        return
    my_module.custom_log(f'you select {call},{call_legs}')
    legs_chans_ips = None
    
    if len(log_files) > 0:
        if len(call_legs) > 1:
            legs_chans_ips = my_module.rtp_count(call_legs, log_files) 
        delete_old_sip_file()
        sips = None
        if  legs_chans_ips is not None:
            my_module.custom_log('rec日志分析', my_module.logging.CRITICAL)
            sips = my_module.sip_dialog(legs_chans_ips, log_files)
        elif call and len(call_legs) > 0 :
            my_module.custom_log('Mysip日志分析', my_module.logging.CRITICAL)
            sips = my_module.sip_masip(call, call_legs)

        else:
            my_module.custom_log('没有可以分析的日志内容', my_module.logging.CRITICAL)  
            return  
        draw.draw_sip()        
        #my_module.custom_log(my_module.A_VERY_LONG_LINE, my_module.logging.CRITICAL)

   
    else:
        my_module.custom_log('没有可以分析的日志内容', my_module.logging.CRITICAL)
                


if __name__ == '__main__':  
    main()