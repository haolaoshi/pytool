import logging
import os
import re
import sys
import unicodedata
from colorama import Fore, Back, Style, init  
  
# 初始化colorama（只需要调用一次）  
init()  
# 打印绿色文字  
#print(Fore.GREEN + '这是绿色文字')  
# 重置颜色到默认  
#print(Style.RESET_ALL)  
# 打印红色文字  
#print(Fore.RED + '这是红色文字')  
# 如果你需要同时改变背景色和文本色  
#print(Back.GREEN + Fore.BLACK + '绿色背景黑色文字')  
# 重置所有设置  
#print(Style.RESET_ALL)

MAX_LINE_WIDTH = 66
MAX_TEXT_WIDTH = 50

def get_year():
    from datetime import datetime  
    now = datetime.now()   
    year = now.year   
    return year

THIS_YEAR = f'{get_year()}'

logging.basicConfig(level=logging.DEBUG, format="%(message)s", handlers=[
                    logging.StreamHandler(sys.stdout), logging.FileHandler("log.txt")])

level_colors = {
    logging.DEBUG: '\033[94m',
    logging.INFO: '\033[92m',
    logging.WARNING: '\033[93m',
    logging.ERROR: '\033[91m',
    logging.CRITICAL: '\033[95m'
}

level_descriptions = {
    logging.DEBUG: 'DEBUG',
    logging.INFO: 'INFO',
    logging.WARNING: 'WARNG',
    logging.ERROR: 'ERROR',
    logging.CRITICAL: 'FATAL'
}


def custom_log(message, level=logging.DEBUG, output='screen'):
    color = level_colors.get(level)
    # description = level_descriptions.get(level, '')
    description = ""
    if output == 'screen':
        logging.log(level, f"{color} {message}\033[0m")
    elif output == 'file':
        logging.log(level, message)
 
def extract_ip_addresses(text):
    ip_address = None

    pattern = r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'

    for line in text.split('\n'):
        match = re.search(pattern, line)
        if match:
            ip_address = match.group()

    return ip_address


def ajust_name(agent):
    if agent is None:
        return "未知"
    elif agent.startswith("CallManager"):
        return "CM"
    elif agent.startswith("maSIP"):
        return "Masip"
    else:
        return agent


def parse_sip_logs(file_path): 
 
    messages = {}
    contacts = {}
    partis = {}

    local_ip = None

    # 打开文件进行逐行读取
    with open(file_path, 'r') as file:
        lines = file.readlines()

    num_lines = len(lines)
    i = 0
    call_id = ""

    while i < num_lines:
        # 解析日期时间和源/目标IP地址
        line = lines[i]
        if line[0] == '[':
            timestamp = line.split()[0].strip('[]')

            ip_info = line.split()[5]
            ip = extract_ip_addresses(ip_info)

            direction = 'send' if 'send to' in line else 'recv'

            # 解析SIP命令和报文内容
            sip_command = lines[i + 1].strip()

            k = 0
            sip_message = ""
            msg_line = lines[i + k].strip()
            while msg_line != '':
                sip_message = f'{sip_message}\n{msg_line}'
                k = k + 1
                if i + k == num_lines:
                    break
                msg_line = lines[i + k].strip()
                if "Call-ID" in msg_line:
                    call_id = msg_line.split()[1]

            i = i + 1

            message = f'{sip_command}\n{sip_message}'
            # 判断Contact字段并添加到列表中
            if 'Contact' in sip_message:
                contact_field = sip_message.split(
                    'Contact: ')[1].split('\n')[0]
                contact_ip = extract_ip_addresses(contact_field)

                userAgent = sip_message.split(
                    'User-Agent: ')[1].split('\n')[0] if 'User-Agent' in sip_message else None

                userAgent = ajust_name(userAgent)
                if contact_ip not in contacts:
                    contacts[contact_ip] = {
                        'agent': userAgent, 'call_id': call_id, 'contact_field': contact_field}
            else:
                contact_ip = None

            local_ip = contact_ip if local_ip is None and direction == "send" and contact_ip is not None else None

            if call_id not in partis:
                partis[call_id] = {}

            if local_ip is not None:
                partis[call_id]['local_ip'] = local_ip
                partis[call_id]['local'] = userAgent
                partis[call_id]['local_field'] = contact_field
            remote_ip = ip if direction == "recv" and contact_ip is not None else None
            if remote_ip is not None:
                partis[call_id]['remote_ip'] = remote_ip
                partis[call_id]['remote'] = userAgent
                partis[call_id]['remote_field'] = contact_field

            reason = sip_message.split('Reason: ')[1].split('\n')[0] if contains_error_code(
                sip_command) and 'Reason: ' in sip_message else None
            # 将消息添加到字典中，使用时间戳作为键
            if timestamp in messages:
                last_digit_index = len(timestamp) - 1
                last_digit = int(timestamp[last_digit_index])
                last_digit += 1
                new_last_digit = str(last_digit)
                timestamp = timestamp[:last_digit_index] + new_last_digit

            msg_from_ip = local_ip if direction == "send" else ip
            messages[timestamp] = {
                'ip': msg_from_ip, 'direction': direction, 'message': message, 'call_id': call_id, 'reason': reason}

            i = i + k
        elif line.startswith(THIS_YEAR):
            timestamp = line.split()[1]
            ip_info = line.split()[8]
            ip = extract_ip_addresses(ip_info)

            direction = 'send' if 'send to' in line else 'recv'

            # 解析SIP命令和报文内容
            sip_command = lines[i + 1].strip()

            k = 0
            sip_message = ""
            msg_line = lines[i + k].strip()
            while msg_line != '':
                sip_message = f'{sip_message}\n{msg_line}'
                k = k + 1
                if i + k == num_lines:
                    break
                msg_line = lines[i + k].strip()
                if "Call-ID" in msg_line:
                    call_id = msg_line.split()[1]

            i = i + 1

            message = f'{sip_command}\n{sip_message}'
            # 判断Contact字段并添加到列表中
            if 'Contact' in sip_message:
                contact_field = sip_message.split(
                    'Contact: ')[1].split('\n')[0]
                contact_ip = extract_ip_addresses(contact_field)

                userAgent = sip_message.split(
                    'User-Agent: ')[1].split('\n')[0] if 'User-Agent' in sip_message else None

                userAgent = ajust_name(userAgent)
                if contact_ip not in contacts:
                    contacts[contact_ip] = {
                        'agent': userAgent, 'call_id': call_id, 'contact_field': contact_field}
            else:
                contact_ip = None

            local_ip = contact_ip if local_ip is None and direction == "send" and contact_ip is not None else None

            if call_id not in partis:
                partis[call_id] = {}

            if local_ip is not None:
                partis[call_id]['local_ip'] = local_ip
                partis[call_id]['local'] = userAgent
                partis[call_id]['local_field'] = contact_field
            remote_ip = ip if direction == "recv" and contact_ip is not None else None
            if remote_ip is not None:
                partis[call_id]['remote_ip'] = remote_ip
                partis[call_id]['remote'] = userAgent
                partis[call_id]['remote_field'] = contact_field

            reason = sip_message.split('Reason: ')[1].split('\n')[0] if contains_error_code(
                sip_command) and 'Reason: ' in sip_message else None
            # 将消息添加到字典中，使用时间戳作为键
            if timestamp in messages:
                last_digit_index = len(timestamp) - 1
                last_digit = int(timestamp[last_digit_index])
                last_digit += 1
                new_last_digit = str(last_digit)
                timestamp = timestamp[:last_digit_index] + new_last_digit

            msg_from_ip = local_ip if direction == "send" else ip
            messages[timestamp] = {
                'ip': msg_from_ip, 'direction': direction, 'message': message, 'call_id': call_id, 'reason': reason}

            i = i + k

    return contacts, messages, partis


def ues_show(callid, messages, contacts):
    ueas = None
    uebs = None

    print(contacts)

    custom_log(callid)
    for m in messages.values():
        if 'recv' == m['direction'] and callid == m['call_id']:
            ipa = m['ip']
            agent = contacts[ipa]['agent']
            field = contacts[ipa]['contact_field']
            uebs = f'{field}{agent}'
        elif 'send' == m['direction'] and callid == m['call_id']:
            for ips in contacts.keys():
                if ips == m['ip']:
                    agent = contacts[ips]['agent']
                    field = contacts[ips]['contact_field']
                    ueas = f'{field}{agent}'

    # print(len(ueas), len(uebs), (MAX_LINE_WIDTH))
    if len(ueas) + len(uebs) > (MAX_LINE_WIDTH):
        custom_log(ueas)
        while (len(uebs) < MAX_LINE_WIDTH):
            uebs = ' ' + uebs
        custom_log(uebs)
    else:
        while (len(ueas) + len(uebs) < MAX_LINE_WIDTH):
            ueas = ueas + '-'
        custom_log(f'{ueas}{uebs}')


def party_show(party):
    print(party)
    # {'remote_ip': '10.30.30.17', 'remote': 'Masip', 'remote_field': '<sip:17@10.30.30.17:5060>',
    # 'local_ip': '10.30.30.16', 'local': 'CM', 'local_field': '<sip:15058450216@10.30.30.16:8000>'}
    local = party['local']
    local_ip = party['local_ip']
    local_field = party['local_field']
    ueas = f'{local}[{local_ip}]'
    if "@" in local_field and ">" in local_field:
        ip_and_port = local_field.split("@")[1].split(">")[0]
        ueas = f'{local}[{ip_and_port}]'
    remote = party.get('remote',None)
    remote_ip = party.get('remote_ip',None)
    remote_field =party.get('remote_field',None)
    if remote is None and remote_ip is None and remote_field is None:  
        custom_log(f"This call has no remote devices!!!", logging.FATAL)
        return 

    uebs = f'{remote}[{remote_ip}]'
    #print(uebs, remote_field)
    
    if "@" in remote_field and ">" in remote_field:
        ip_and_port = remote_field.split("@")[1].split(">")[0]
        uebs = f'{remote}[{ip_and_port}]'

    # 获取字符串的字节数
    byte_count = len(uebs.encode('utf-8'))
    # print("uebs字节数：", byte_count)

    # 获取字符串的字符数
    char_count = len(
        [c for c in uebs if unicodedata.east_asian_width(c) != 'F'])

    # print("字符数：", char_count)

    Compensation = (byte_count - char_count)/2

    if len(ueas) + len(uebs) > (MAX_LINE_WIDTH):
        custom_log(ueas)

        while (len(uebs) < (MAX_LINE_WIDTH - Compensation)):
            uebs = ' ' + uebs
        custom_log(uebs)

    else:
        while ((len(ueas) + len(uebs)) < (MAX_LINE_WIDTH - Compensation)):
            ueas = ueas + ' '
        custom_log(f'{ueas}{uebs}')


def contains_error_code(string):
    pattern = r'\b[4-6]\d{2}\b'
    matches = re.findall(pattern, string)

    if matches:
        return True


def contains_warning_code(string):
    pattern = r'CANCEL'
    matches = re.findall(pattern, string)

    if matches:
        return True


def print_sip_messages(contacts, messages, parties):
    # 获取UE-A和UE-B的IP地址
    # print(contacts)
    print('\n')
    # 打印UE-A和UE-B的IP地址
 
    #根据每一个call-id进行处理
    for call_id in parties.keys():
        print_title = True
        # 按时间顺序打印每个报文
        for timestamp in sorted(messages.keys()):
            message = messages[timestamp]
            ip = message['ip']
            direction = message['direction']
            sip_command = message['message'].split('\n')[0]

            reason = message['reason'] if contains_error_code(
                sip_command) else None
            if call_id != message['call_id']:
                #print_title = True
                continue

            if print_title:
                print(call_id)
                # ues_show(call_id, messages, contacts)
                party = parties[call_id]
                party_show(party)
                print_title = False
            # else:
            #     print("\n")
            #     call_id = message['call_id']
            #     print(call_id)
            #     # ues_show(call_id, messages, contacts)
            #     party = parties[call_id]
            #     party_show(party)

            if sip_command.startswith("SIP"):
                sip_command = sip_command[8:20]
            elif "@" in sip_command:
                sip_command = sip_command.split("@")[0]
            else:
                sip_command = sip_command[0:7]

            sip_command = sip_command.strip()
            command_length = len(sip_command)

            if command_length < 8:
                left_padding = '-' * int((MAX_TEXT_WIDTH - command_length) / 2)
                right_padding = '-' * \
                    (MAX_TEXT_WIDTH - command_length - len(left_padding))
                sip_command = f'{left_padding}{sip_command}{right_padding}'
            elif command_length < MAX_TEXT_WIDTH:
                sip_command = sip_command.center(MAX_TEXT_WIDTH, "-")
            else:
                exit(1)

            # 根据报文的方向绘制箭头虚线
            arrow_line = f'{timestamp} '

            if direction == 'send':
                arrow_line += f'|{sip_command}>|'
            elif direction == 'recv':
                arrow_line += f'|<{sip_command}|'
            if contains_error_code(sip_command):
                custom_log(arrow_line, logging.ERROR)
            elif contains_warning_code(sip_command):
                custom_log(arrow_line, logging.WARN)
            else:
                custom_log(arrow_line, logging.INFO)

            if reason is not None:
                custom_log(f"{ip} say : {reason}", logging.FATAL)

def draw_sip(file_path='sip.txt'):
    contacts, messages, parties = parse_sip_logs(file_path)
    print_sip_messages(contacts, messages, parties)

if __name__ == "__main__":
 
    file_path = 'sip.txt'
    current_path = os.getcwd() 
    
    file_path = os.path.join(current_path,file_path)
    file_path = rf'D:\dingtalk\国盛\国盛证券主叫1058被叫18279166752\sip.txt'
    draw_sip(file_path)
