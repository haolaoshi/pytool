#!/usr/bin/python
# -*- coding: UTF-8 -*-
from collections import Counter
from datetime import datetime, timedelta
from datetime import datetime, timedelta
import re
import os
import sys
import argparse
import matplotlib.pyplot as plt
import numpy as np
import matplotlib as mpl
import json
import logging
 
A_VERY_LONG_LINE = "----------------------------------------------------------------------------"
'''
loge 日志分析程序 
输入一个号码 ，或者录音文件，输出对应通话的分析结果

- 1.确定日志范围，后面分析都基于这个日志范围，避免全局搜索 -logs
- 2.列出有效通话，如果号码命中多个通话，让用户选择分析哪一通；后面分析都基于这个 - obj选择
- 3.提取录音/通话开始-结束
- 4.丢包统计 ,分析RTP CallLeg
- 5.终端分析 ,识别通话使用的话机型号,终端型号,IP:PORT
- 6.座席分析, 在接待客户期间,座席执行了哪些指令

CallLegBuddy 对象,记录call,callLeg,channel, call-id ,agent(id,phone,uid), customer(phone), record

'''


MAX_LINE_WIDTH = 66
MAX_TEXT_WIDTH = 50

def get_year():
    from datetime import datetime  
    now = datetime.now()   
    year = now.year   
    return year

THIS_YEAR = f'{get_year()}'

def extract_ip_addresses(text):
    ip_address = None

    pattern = r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'

    for line in text.split('\n'):
        match = re.search(pattern, line)
        if match:
            ip_address = match.group()

    return ip_address


def parse_sip_logs(file_path):
    # 创建空字典，用于存储报文的时间和SIP命令
    messages = {}

    # 创建空列表，用于存储不同的Contact字段
    contacts = {}

    # 打开文件进行逐行读取
    # with open(file_path, 'r') as file:
    #     lines = file.readlines()
    lines = file_path.splitlines()

    num_lines = len(lines)
    i = 0

    while i < num_lines:
        # 解析日期时间和源/目标IP地址
        line = lines[i]
        k = 0
        if line.startswith(THIS_YEAR):
            timestamp = line.split()[1]
            ip_info = line.split()[8]
            ip = extract_ip_addresses(ip_info)

            direction = 'send' if 'send to' in line else 'recv'

            # 解析SIP命令和报文内容
            sip_command = lines[i + 1].strip()

            sip_message = ""
            msg_line = lines[i + k].strip()
            while msg_line != '':
                sip_message = f'{sip_message}\n{msg_line}'
                k = k + 1
                if i + k == num_lines:
                    break
                msg_line = lines[i + k].strip()
            i = i + 1

            message = f'{sip_command}\n{sip_message}'
            # 判断Contact字段并添加到列表中
            if 'Contact' in sip_message:
                contact_field = sip_message.split(
                    'Contact: ')[1].split('\n')[0]
                contact_field = extract_ip_addresses(contact_field)
                if contact_field not in contacts:
                    contacts[contact_field] = set()

                    if 'User-Agent' in sip_message:
                        userAgent = sip_message.split(
                            'User-Agent: ')[1].split('\n')[0]
                        contacts[contact_field].add(userAgent)

            # 将消息添加到字典中，使用时间戳作为键
            messages[timestamp] = {
                'ip': ip, 'direction': direction, 'message': message}

        i += k if k > 1 else 1

    return contacts, messages


def print_sip_messages(contacts, messages): 
    # 获取UE-A和UE-B的IP地址
    print(contacts)
    print('\n')
    # 打印UE-A和UE-B的IP地址
    ueas = None
    uebs = None

    for m in messages.values():
        if 'recv' == m['direction']:
            ipa = m['ip']
            uebs = f'{ipa}{contacts[ipa]}'
        elif 'send' == m['direction'] and uebs is not None:
            for ips in contacts.keys():
                if ips == m['ip']:
                    continue
                else:
                    ueas = f'{ips}{contacts[ips]}'
    if ueas is None:
        exit(2)

    # print(len(ueas), len(uebs), (MAX_LINE_WIDTH))
    if len(ueas) + len(uebs) > (MAX_LINE_WIDTH):
        print(ueas)
        while (len(uebs) < MAX_LINE_WIDTH):
            uebs = ' ' + uebs
        print(uebs)
    else:
        while (len(ueas) + len(uebs) < MAX_LINE_WIDTH):
            ueas = ueas + '-'
        print(f'{ueas}{uebs}')

    # 按时间顺序打印每个报文
    for timestamp in sorted(messages.keys()):
        message = messages[timestamp]
        ip = message['ip']
        direction = message['direction']
        sip_command = message['message'].split('\n')[0]

        if sip_command.startswith("SIP"):
            sip_command = sip_command[8:20]
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

        print(arrow_line)


class MediaChannelPlotter:
    def __init__(self, data,  show_received=False, show_selected=False):
        self.data = data
        self.show_received = show_received
        self.show_selected = show_selected

    def save(self, i):
        fig = plt.gcf()
        fig.savefig(f'{i}.png')
        plt.close(fig)

    def plot_new(self, i_name=0, comment=None):
        channels = {}
        timestamps = {}
        start_time = None

        for line in self.data:
            match = re.match(
                r'^(\d+:\d+:\d+\.\d+) MediaChannel\[(\d+)\] (\d+)/(\d+)', line)
            if match:
                # timestamp = datetime.strptime(match.group(1), '%H:%M:%S.%f')
                timestamp = datetime.datetime.strptime(
                    match.group(1), '%H:%M:%S.%f')
                channel = match.group(2)
                if start_time is None:
                    start_time = timestamp
                if channel not in channels:
                    channels[channel] = {'received': [], 'lost': []}
                lost = int(match.group(3))
                received = int(match.group(4))
                channels[channel]['received'].append(received)
                channels[channel]['lost'].append(lost)
                t = (timestamp - start_time).total_seconds()
                timestamps.setdefault(channel, []).append(t)

        # 绘制图表，使用 numpy.linspace() 在时间范围内生成间隔合适的刻度
        plt.figure(figsize=(10, 6))
        fig = plt.gcf()
        for i, channel in enumerate(sorted(channels.keys())):
            print(channel)
            if self.show_selected and (int(channel) & 1) > 0:
                continue
            t = timestamps[channel]
            x = np.linspace(t[0], t[-1], len(channels[channel]['lost']))
            if self.show_received:
                plt.plot(x, channels[channel]['received'],
                         color=f'C{i}', label=f'MediaChannel[{channel}]received')
            if self.show_selected:
                i = int(i/2)
                y_lost = np.array(channels[channel]['lost'])
                y_lost = np.where(y_lost > 250, 250, y_lost)  # 超出范围设为 250
                # 超出范围的设置为粗线条，其他为细线条
                linewidths = np.where(y_lost == 250, 2, 0.5)
                plt.plot(x, y_lost, linestyle='--', color=f'C{i}', linewidth=linewidths[0],
                         label=f'MediaChannel[{channel}] lost')
            else:
                y_lost = np.array(channels[channel]['lost'])
                y_lost = np.where(y_lost > 250, 250, y_lost)  # 超出范围设为 250
                # 超出范围的设置为粗线条，其他为细线条
                linewidths = np.where(y_lost == 250, 2, 0.5)
                plt.plot(x, y_lost, linestyle='--', color=f'C{i}', linewidth=linewidths[0],
                         label=f'MediaChannel[{channel}] lost')

        # 调整图表格式

        if comment:
            title = f'{i_name} Statistics'
            for str in comment:
                title = f'{title}\n{str}'
            plt.title(f'{title}')
        else:
            plt.title(f'{i_name} Statistics')
        plt.xlabel('Time')
        plt.ylabel('Number of Packets')
        plt.legend(loc='upper left')
        plt.xticks(np.linspace(0, x[-1], 10),
                   [datetime.datetime.strptime(start_time.strftime('%H:%M:%S.%f'), '%H:%M:%S.%f') +
                    datetime.timedelta(seconds=int(t)) for t in np.linspace(0, x[-1], 10)],
                   rotation=20, ha='right')
        # 修改时间格式字符串，并相应地更改 datetime.strptime() 函数中的格式字符串
        plt.gca().xaxis.set_major_formatter(
            mpl.ticker.FuncFormatter(lambda x, _: (start_time + datetime.timedelta(seconds=x)).strftime("%H:%M:%S.%f")[:-4]))
        plt.grid()
        # 添加文字说明

        plt.ylim((0, 250))  # y 轴限制在 0-250 之间

        # 显示或保存图表
        print(i_name, ".png")
        if i_name == 0:
            plt.show()
        else:
            fig.savefig(f'{i_name}.png')
            plt.close(fig)
            return 0

    def plot(self, i_name=0, comment=None):
        channels = {}
        timestamps = {}
        start_time = None

        for line in self.data:
            match = re.match(
                r'^(\d+:\d+:\d+\.\d+) MediaChannel\[(\d+)\] (\d+)/(\d+)', line)
            if match:
                # timestamp = datetime.strptime(match.group(1), '%H:%M:%S.%f')
                timestamp = datetime.datetime.strptime(
                    match.group(1), '%H:%M:%S.%f')
                channel = match.group(2)
                if start_time is None:
                    start_time = timestamp
                if channel not in channels:
                    channels[channel] = {'received': [], 'lost': []}
                lost = int(match.group(3))
                received = int(match.group(4))
                channels[channel]['received'].append(received)
                channels[channel]['lost'].append(lost)
                t = (timestamp - start_time).total_seconds()
                timestamps.setdefault(channel, []).append(t)

        # 绘制图表，使用 numpy.linspace() 在时间范围内生成间隔合适的刻度
        plt.figure(figsize=(10, 6))
        fig = plt.gcf()
        for i, channel in enumerate(sorted(channels.keys())):
            print(channel)
            if self.show_selected and (int(channel) & 1) > 0:
                continue
            t = timestamps[channel]
            x = np.linspace(t[0], t[-1], len(channels[channel]['lost']))
            if self.show_received:
                plt.plot(x, channels[channel]['received'],
                         color=f'C{i}', label=f'MediaChannel[{channel}]received')
            if self.show_selected:
                i = int(i/2)
                plt.plot(x, channels[channel]['lost'], linestyle='--',
                         color=f'C{i}', label=f'MediaChannel[{channel}] lost')
            else:
                plt.plot(x, channels[channel]['lost'], linestyle='--',
                         color=f'C{i}', label=f'MediaChannel[{channel}] lost')

        # 调整图表格式

        if comment:
            title = f'{i_name} Statistics'
            for str in comment:
                title = f'{title}\n{str}'
            plt.title(f'{title}')
        else:
            plt.title(f'{i_name} Statistics')
        plt.xlabel('Time')
        plt.ylabel('Number of Packets')
        plt.legend(loc='upper left')
        plt.xticks(np.linspace(0, x[-1], 10),
                   [datetime.datetime.strptime(start_time.strftime('%H:%M:%S.%f'), '%H:%M:%S.%f') +
                    datetime.timedelta(seconds=int(t)) for t in np.linspace(0, x[-1], 10)],
                   rotation=20, ha='right')
        # 修改时间格式字符串，并相应地更改 datetime.strptime() 函数中的格式字符串
        plt.gca().xaxis.set_major_formatter(
            mpl.ticker.FuncFormatter(lambda x, _: (start_time + datetime.timedelta(seconds=x)).strftime("%H:%M:%S.%f")[:-4]))
        plt.grid()
        # 添加文字说明

        # 显示或保存图表
        print(i_name, ".png")
        if i_name == 0:
            plt.show()
        else:
            fig.savefig(f'{i_name}.png')
            plt.close(fig)
            return 0


def is_filename_numeric(filename):
    # 提取文件名部分（去掉后缀）
    filename_without_extension = filename[:filename.rindex('.')]
    # print(filename_without_extension)
    # 使用正则表达式判断文件名是否为纯数字
    # pattern = r'^\d+$'
    pattern = r'^[0-9_]+$'
    return re.match(pattern, filename_without_extension) is not None


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


def get_address_from_callleg(line, num):
    #pattern = r"CallLeg\[" + str(num) + "\] from\s(.+?)\sto\s(.+?)\s"
    escaped_num = re.escape(str(num))  # 转义 num 中的特殊字符  
    pattern = r"CallLeg\[{}\] from\s([^\s]+)\sto\s([^\s]+)\s".format(escaped_num)  
    match = re.search(pattern, line)
    if match:
        from_address = match.group(1).split("<")[1][:-1]  # 提取from地址，并去除"<>"
        to_address = match.group(2)
        address_str = "CallLeg[{}] from {} to {}".format(
            num, from_address, to_address)
        return address_str
    else:
        return None


class UE:
    def __str__(self):
        return self.role + " [ " + self.ip + " : " + self.port + " ] " + self.name

    def __hash__(self) -> int:
        return hash(self.ip+self.port+self.name)

    def __eq__(self,  other) -> bool:
        if self.name == other.name and self.port == other.port and self.ip == other.ip:
            return True
        else:
            return False

    def __init__(self, ip, port, name, role):
        self.ip = ip
        self.port = port
        self.name = name
        self.role = role


class Connection:
    def __str__(self):
        return self.audioConn() + "," + self.videoConn()

    def __init__(self, c, audio, video):
        self.c = c
        self.audio = audio
        self.video = video

    def audioConn(self):
        return self.c+":"+self.audio

    def videoConn(self):
        return self.c+":"+self.video


def is_neighbour(time_str1, time_str2):
    # 将字符串转换为datetime对象
    time1 = datetime.strptime(time_str1, '%Y-%m-%d %H:%M:%S.%f')
    time2 = datetime.strptime(time_str2, '%Y-%m-%d %H:%M:%S.%f')

    # 计算两个时间的差值
    time_diff = abs(time1 - time2)
    one_second = timedelta(seconds=1)

    # 比较差值是否在1秒内
    return time_diff <= one_second


class TapeJour:
    def __init__(self, file, begin, end):
        self.file = file
        self.begin = begin
        self.end = end

    def __str__(self):
        return f"FILENAME: {self.file} , BEGIN_TIME: {self.begin}, END_TIME: {self.end}"


class VoceCall:
    def __init__(self, call):
        self.call = call

    def setCallLeg(self, leg):
        if self.left is None:
            self.left = leg
        elif self.leg > leg:
            self.right = self.left
            self.left = leg
        elif self.left == leg:
            pass


class CallLegBuddy:
    def __init__(self, left_string, right_string):
        self.record_duration = ""
        self.record_end = ""
        self.record_name = ""
        self.record_start = ""

        self.call = ""
        self.direction = ""
        self.customer = ""
        self.agent = ""

        self.left_call_id = ""
        self.right_call_id = ""

        self.left_channel = ""
        self.right_channel = ""

        self.left_connection = []
        self.right_connection = []

        self.left_time = re.search(
            r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+)', left_string).group(1)
        self.left_id = re.search(r'CallLeg\[(\d+)\]', left_string).group(1)

        self.left_from = re.search(r"from\s(.+?)\s+to", left_string).group(1)
        # self.left_from = re.search(r'from\s+<([^>]+)>', left_string).group(1)
        self.left_to = re.search(r'to\s+<([^>]+)>', left_string).group(1)

        self.right_time = re.search(
            r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+)', right_string).group(1)
        self.right_id = re.search(r'CallLeg\[(\d+)\]', right_string).group(1)

        self.right_from = re.search(r"from\s(.+?)\s+to", right_string).group(1)
        # self.right_from = re.search(r'from\s+<([^>]+)>', right_string).group(1)
        self.right_to = re.search(r'to\s+<([^>]+)>', right_string).group(1)

    # 对齐显示
    def __str__(self):
        return f"ID: {self.left_id}, Time: {self.left_time:<10}, From: {self.left_from:<32}, To: {self.left_to}\n" \
            f"ID: {self.right_id}, Time: {self.right_time:<10}, From: {self.right_from:<32}, To: {self.right_to}\n"

    def in_pair(self):
        return is_neighbour(self.right_time, self.left_time) and (int(self.right_id) - int(self.left_id) == 1)

    def get_direction(self):
        if not self.in_pair():
            return None
        d = 0
        matches = re.findall(r"(0|1)\d{10}", self.left_from)
        if matches:
            d = 0
        if "8000" in self.left_from and "7000" in self.left_to:
            d = 1
        elif "7000" in self.right_from:
            d = 1
        elif "8000" in self.left_to and "8000" in self.right_from:
            d = 1
        else:
            d = 0

        self.direction = "呼入" if d == 0 else "外呼"
        return self.direction

    def setTapeJour(self, start, type, duration, name):
        # print(f"setTapeJour type={type}.")
        if "769" == type[0:3]:
            self.record_start = start
        elif "514" == type[0:3]:
            self.record_duration = duration[0:-1]
            self.record_end = start
            self.record_name = name
        elif name:
            self.record_name = name

    def getTapeJour(self):
        if self.record_duration:
            return f"TapeJour|{self.record_start}|{self.record_end}|{int(self.record_duration)/1000}|{self.record_name}"

    def showConnection(self):
        list_a = set(self.left_connection)
        print("Left Connection : ", list_a)
        list_b = set(self.right_connection)
        print("Rigth Connection : ", list_b)


def get_valid_input(N):
    while True:
        user_input = input(f"请输入一个数字1到{N}之间的值：")

        try:
            number = int(user_input)
        except ValueError:
            print("输入无效！请输入一个数字。")
            break

        if 1 <= number <= N:
            return number
        else:
            print("输入无效！请输入一个数字1到N之间的值。")


def chooseOneCall(phone_no, files):
    call_data = {}
    call_time = {}

    v_gateway = []
    for file in files:
        with open(file, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.read()  # 读取所有内容
            #排除是不是指定网关外呼
            pattern = r'2.*IPCC30 Callback: AppID=.*usrDo\(\"81.*{}.*'.format(re.escape(phone_no))  
             
            match = re.search(pattern,lines)
            if match:
                callbar_info = match.group().split() 
                if len(callbar_info[10].split('@')) < 2:
                    print(callbar_info[10].split('@'))
                    continue
                
                gw = callbar_info[10].split('@')[1].split('"')[0]
                v_gateway.append(gw)
                custom_log(f"指定了网关外呼:{gw}", logging.FATAL)

                continue

            # 按手机号定位
            legs = []
            matches = re.finditer(rf"[2].*CM CallLeg.*{phone_no}", lines)
            for match in matches:
                # print(match.group())
                leg = match.group().split()[5]
                legs.append(leg)

            if len(legs) > 0:
                listsleg = set(legs)
                for l in listsleg:
                    leg_id = l.split("[")[1].split("]")[0]
                    # Call[54334] add CallLeg[54335]
                    pattern = rf"[2].*CM Call\[(\d+)\].*CallLeg\[{leg_id}\]"
                    matches = re.finditer(pattern, lines)
                    for mlt in matches:
                        # print(mlt.group())
                        time = mlt.group()[0:24]
                        call_id = mlt.group().split()[5].split(
                            "[")[1].split("]")[0]

                        if call_id not in call_data:
                            call_data[call_id] = set()
                        call_data[call_id].add(leg_id)
                        if call_id not in call_time:
                            call_time[call_id] = set()
                        call_time[call_id] = time

            # 按录音定位
            wav_ptrn = r"[2].*CM Call\[(\d+)\] record to .*?/(" + \
                re.escape(phone_no)+")"

            ws = re.finditer(wav_ptrn, lines)
            for w in ws:
                call_id = w.group().split("[")[1].split("]")[0]
                ss = re.finditer(
                    rf"[2].*CM Call\[{call_id}\] add CallLeg\[(\d+)\],", lines)
                for s1 in ss:
                    # print(s1.group())
                    leg_id = s1.group().split("[")[2].split("]")[0]
                    time = s1.group()[0:24]
                    if call_id not in call_data:
                        call_data[call_id] = set()
                    call_data[call_id].add(leg_id)
                    if call_id not in call_time:
                        call_time[call_id] = set()
                    call_time[call_id] = time

    if len(call_data) > 1:
        L = list(call_data.keys())
        L.sort()
        ii = 0
        for callid in L:
            ii = ii + 1
            custom_log(f"[{ii}] {callid} {call_time[callid]}", logging.INFO)
        # for i, (call_id, leg_ids) in enumerate(call_data.items(), start=1):
        #     # print(f"[{i}] {call_id}: {call_time[call_id]}")
        #     custom_log(f"[{i}] {call_id} {call_time[call_id]}", logging.INFO)
        # 让用户选择编号
        selection = int(input("请根据开始时间，选择分析第几通电话: "))
        # 根据用户选择的编号获取对应的元素
        if selection >= 1 and selection <= len(call_data):
            selected_call = L[selection - 1]
            # print(f"选择分析: {selected_call}: {call_data[selected_call]}")
            return selected_call, call_data[selected_call]
    elif len(call_data) == 0  and len(v_gateway) == 0:
        custom_log("no call ", logging.FATAL)
    elif len(v_gateway) > 0:
        gw = v_gateway.pop()
        print('搜索{gw}在masip日志中....')
        prepared_log_files = []
        for root, dirs, files in os.walk('./'):
            for file in files:
                if ('maSIP' in file or 'masip' in file) and file.endswith('.log'):
                    prepared_log_files.append(os.path.join(root, file))
        isvalid_log =False
        for file in prepared_log_files:
            with open(file, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
                found_gw = False
                write_sip = False
                time = "" 
                last_line_begin = ""
                
                for line in lines:
                    if not isvalid_log:
                        if f'{phone_no}@{gw}' in line:
                            print(f"开始录制{line}") 
                            isvalid_log = True 
                        else:
                            continue 
                    pattern = r'UdpTransport::process\(\),\s+send\s+to\s+\[\s*{}\s*:\d+\s*\]:'.format(re.escape(gw))  

                    match = re.search(pattern,line)
                    if match: 
                        time = line.split()[0] 
                        found_gw = True 
                        last_line_begin = line

                    pattern = r'INVITE sip:{}@{}'.format(re.escape(phone_no), re.escape(gw))    
                    match = re.search(pattern,line)
                    if match:
                        write_sip = True 
                        found_gw = False
                        #print(last_line_begin)
                        last_line_begin = ""
                        
                    if write_sip and "Call-ID" in line:
                        callid = line.split(':')[1]
                        write_sip = False 
                        call_data[callid] = time
                        #print(line)
                    elif write_sip :
                        #print(line)
                        pass
        if len(call_data) > 0:             
            ii = 0
            
            L = list(call_data.keys())
            L.sort()   
            for callid in L:
                ii = ii + 1
                custom_log(f"[{ii}] {call_data[callid]}{callid} ", logging.INFO)                 
                 
        
            selection = int(input("请根据开始时间，选择分析第几通电话: ")) 
            if selection >= 1 and selection <= ii:
                selected_call = L[selection - 1]
                print(f"选择分析: {call_data[selected_call]}{selected_call}{prepared_log_files}")
                return selected_call, prepared_log_files


        for time in call_time:
            custom_log(f"{time} {callid}", logging.INFO)
        # first_key
        return "",""
                        
            

    else:
        first_key = next(iter(call_data))
        first_time = call_time[first_key]
        custom_log(f"{first_key} {first_time}", logging.INFO)
        # first_key
        return first_key, call_data[first_key]


def duration_cal(call, logs):

    begin = end = record = ""
    tapeObj = None

    for file in logs:
        # 2023-07-26 13:49:33.879 049805 I RT The ((Router *)0x0xf6b28010)->doCallRecordStart is invoked on the Call[54334] start record
        # 2023-07-26 13:49:49.875 049805 I RT The ((Router *)0x0xf6b28010)->doCallRecordEnd is invoked on the Call[54334] stop record
        # 2023-07-26 13:49:33.903 049805 I CM Call[54334] record to /home/qyuc/rec/record/2023-07-26/6041/54334134933903.wav
        start_pattern = rf"[2].*doCallRecordStart is invoked on the Call\[{call}\]"
        end_pattern = rf"[2].*doCallRecordEnd is invoked on the Call\[{call}\]"
        record_pattern = rf"[2].*I CM Call\[{call}\] record to /.*"
        with open(file, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.read()  # 读取所有内容
            matches = re.finditer(start_pattern, lines)  # 迭代匹配结果
            for match in matches:
                # @print("begin:", match.group()[0:24])  # 输出匹配的内容
                begin = match.group()[0:24]
            matches = re.finditer(end_pattern, lines)  # 迭代匹配结果
            for match in matches:
                # print("end ", match.group()[0:24])  # 输出匹配的内容
                end = match.group()[0:24]
            # 使用正则表达式提取文件名
            matches = re.finditer(record_pattern, lines)  # 迭代匹配结果
            for f1 in matches:
                # 使用正则表达式提取文件名
                f2 = re.search(r'record to (.*)', f1.group())
                # f2 = re.search(r"\d+\.wav", f1.group())
                if f2:
                    tapeObj = TapeJour(f2.group(1), begin, end)
        if tapeObj is not None:
            custom_log(f"{tapeObj}", logging.INFO)
            return tapeObj


def address_put(addrs, leg, chan, conns):
    if leg not in addrs:
        addrs[leg] = {}
    if chan not in addrs[leg]:
        addrs[leg][chan] = set()

    for c in conns:
        if "255" == c[0:3]:
            continue
        if "127" == c[0:3]:
            continue

        addrs[leg][chan].add(c.strip())


def rtp_count(legs, logs):
    if len(legs) == 0:
        print('no legs cannot analyze.')
        return
    
    print('rpt_count',legs,logs)

    if len(legs) == 0 :
        print('no legs.')
        return ""
    
    left_leg = legs.pop()
    right_leg = legs.pop()

    leg_chans_address = {}

    for file in logs:

        with open(file, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.read()  # 读取所有内容
            # grep -E "34233\]\slocal|34232\]\slocal"  rec\(49706\)0726T13_01.log |cut -d" " -f6,10,14

            pattern_a = rf"CM CallLeg\[{left_leg}\] set CallLegChannel\[(\d+)\]"
            chan = re.findall(pattern_a, lines)  # 迭代匹配结果
            for c in chan:  # for match in matches:
                # print(left_leg, c)  # 输出匹配的内容
                # leg_chans[left_leg] = c
                custom_log(f"{left_leg} --> {c}")

                pattern = rf"CM MediaChannel\[{c}\].*?local address is ([^,]+), peer address is ([^,]+)"
                address = re.findall(pattern, lines)
                for a in address:
                    # print(c, a)
                    address_put(leg_chans_address, left_leg, c, a)

                print(leg_chans_address[left_leg])
                pattern_c = rf".*MediaChannel\[{c}\]\sRTP.*"
                statis = re.finditer(pattern_c, lines)
                for s in statis:
                    string = s.group().split()
                    if len(string) > 9:
                        custom_log(
                        f"{string[1]} {string[5]} {string[8]} {string[9]}", logging.INFO)                    
                    else:
                        custom_log(
                        f"{string[1]} {string[5]} {string[8]} ", logging.INFO)

            pattern_b = rf"CM CallLeg\[{right_leg}\] set CallLegChannel\[(\d+)\]"
            chan = re.findall(pattern_b, lines)  # 迭代匹配结果
            for c in chan:  # or match in matches:
                # print(right_leg, c)  # 输出匹配的内容
                # leg_chans[right_leg] = c
                custom_log(f"{right_leg} --> {c}")

                pattern = rf"CM MediaChannel\[{c}\].*?local address is ([^,]+), peer address is ([^,]+)"
                address = re.findall(pattern, lines)
                for a in address:
                    # print(c, a)
                    address_put(leg_chans_address, right_leg, c, a)
                print(leg_chans_address[right_leg])

                pattern_c = rf".*MediaChannel\[{c}\]\sRTP.*"
                statis = re.finditer(pattern_c, lines)
                for s in statis:
                    string = s.group().split() 
                    if len(string) > 9:
                        custom_log(
                        f"{string[1]} {string[5]} {string[8]} {string[9]}", logging.INFO)                    
                    else:
                        custom_log(
                        f"{string[1]} {string[5]} {string[8]} ", logging.INFO)
    return leg_chans_address


def is_valid_ipv4(ip):
    # IPv4地址的正则表达式模式
    pattern = r"^((\d{1,3})\.){3}(\d{1,3})$"

    if re.match(pattern, ip):
        # IP地址合法，进行进一步验证
        octets = ip.split(".")
        if all(0 <= int(octet) <= 255 for octet in octets):
            return True
    return False
 

def whoami(message):
    f = open('sip.txt', 'a', encoding='UTF-8')
    f.write(message)
    f.write("\n")
    f.close()

    ip = port = name = role = ""

    if "send to" in message and "User-Agent" in message:
        match = re.search(r"User-Agent:\s*(.*?)\n", message)
        if match:
            # print("本机设备名:", match.group(1))
            role = "本机设备"
            name = match.group(1)
        # 执行匹配
        match = re.search(r'Contact: <.*@(\d+\.\d+\.\d+\.\d+):(\d+)>', message)
        if match:
            ip = match.group(1)
            port = match.group(2)

    elif "recv from" in message:
        # 来讯网关没有设备名
        match = re.search(r"recv from \[(\d+\.\d+\.\d+\.\d+):(\d+)\]", message)
        if match:
            ip = match.group(1)
            port = match.group(2)
        match = re.search(r"User-Agent:\s*(.*?)\n", message)
        if match:
            # print("对方设备名:", match.group(1))
            role = "对方设备"
            name = match.group(1)
        elif port == "5060":
            # print("猜测是来讯网关")
            log_lines = message.split('\n')
            if log_lines[1].startswith("ACK"):
                return
            role = "对方设备"
            name = "来讯网关?"

    if ip and port and name and role:
        return UE(ip, port, name, role)
    else:
        return None


def extract_sip_messages(log_content, callid):

    sip_messages = []
    current_message = ''
    started = False
    error_occur = False
    Devices = {}

    if callid not in Devices:
        Devices[callid] = set()

    for line in log_content.splitlines():

        if line.startswith(THIS_YEAR) and not started:  # 新的一行，需要判断是不是报文开始
            # 使用正则表达式匹配
            # pattern = fr'\b2023\b.*\bW DM UdpTransport::process\b.*\b((\d{1,3})\.){3}(\d{1,3})\b'
            pattern = fr'\b{THIS_YEAR}\b.*\bW DM UdpTransport::process.*'

            match = re.search(pattern, line)
            if match:
                started = True
                current_message = line + '\n'
        elif (not started) and len(line) > 0 and line[0] == '[':
            # masip日志是个例外
            # pattern = [09:47:48.235] [4140825408] UdpTransport::process(), send to [10.101.73.11:5060]: [
            pattern = fr'.*\bUdpTransport::process.*'

            match = re.search(pattern, line)
            if match:
                started = True
                current_message = line + '\n'            
        # 报文识别结束，或者遇到了新的一行，需要结束
        elif (line.startswith(THIS_YEAR) or len(line) == 0 or "Content-Length" == line[0:14]) and started:
            started = False
            ue = whoami(current_message)
            if ue is not None:
                Devices[callid].add(ue)

            sip_messages.append(current_message)
            current_message = ''
        elif len(line) > 0 and ( line[0] == '[' or len(line) == 0 or "Content-Length" == line[0:14]) and started:
            started = False
            ue = whoami(current_message)
            if ue is not None:
                Devices[callid].add(ue)

            sip_messages.append(current_message)
            current_message = '' 
        # 连续处理SIP报文行，如果判断到Call-ID不对，就清空之前内容。
        elif started and not line.startswith(THIS_YEAR):

            if "Call-ID" == line[0:7] and callid not in line:
                started = False
                current_message = ''
                error_occur = False
            elif "SIP" == line[0:3] and re.search(r"\S+\s([45]\d*)\b", line):
                error_occur = True

            # 这是前一行报文的延续部分，添加到当前报文中
            current_message += line + '\n'
        elif len(line) > 0 and started and (not line[0] == '['): 
            if "Call-ID" == line[0:7] and callid not in line:
                started = False
                current_message = ''
                error_occur = False
            elif "SIP" == line[0:3] and re.search(r"\S+\s([45]\d*)\b", line):
                error_occur = True

            # 这是前一行报文的延续部分，添加到当前报文中
            current_message += line + '\n'
    # # 添加最后一个 SIP 报文
    # if current_message:
    #     sip_messages.append(current_message.strip())
    if error_occur:
        for msg in sip_messages:
            print(msg)

    for callid in Devices.keys():
        for device in Devices[callid]:
            custom_log(f"{device}", logging.CRITICAL)

    return sip_messages

def extract_sip_messages_masip(log_content, callid):

    sip_messages = []
    current_message = ''
    started = False
    right_occur = False
    Devices = {}

    if callid not in Devices:
        Devices[callid] = set()

    for line in log_content.splitlines():

        if (not started) and len(line) > 0 and line[0] == '['  and 'UdpTransport' in line:
            #如果是一个sip的开始，就标记started
            # 然后录制sip，如果call-id符号要求，就提取信息
            # pattern = [09:47:48.235] [4140825408] UdpTransport::process(), send to [10.101.73.11:5060]: [
            pattern = fr'.*\bUdpTransport::process.*'

            match = re.search(pattern, line)
            if match:
                started = True
                current_message = line + '\n'   
        elif len(line) > 0 and ( line[0] == '[' or len(line) == 0 or "Content-Length" == line[0:14]) and started:
            #如果到了SIP结束 ，就决定要不要存储到文件
            
            started = False  
            if right_occur:
                sip_messages.append(current_message) 
                ue = whoami(current_message)
                if ue is not None:
                    Devices[callid].add(ue)
                    print(ue)
            current_message = ''      
        # 连续处理SIP报文行，如果判断到Call-ID不对，就清空之前内容。
        elif len(line) > 0 and started and (not line[0] == '['): 

            # 这是前一行报文的延续部分，添加到当前报文中
            current_message += line + '\n'
            if "Call-ID" in current_message and callid not in current_message:
                started = False
                current_message = ''
                right_occur = False
            elif "Call-ID" in current_message and callid in current_message:
                right_occur = True
        else:
            #不感兴趣的日志走这里
            pass
 
    for callid in Devices.keys():
        for device in Devices[callid]:
            custom_log(f"{device}", logging.CRITICAL)

    return sip_messages

def sip_masip(callid, logs): 
    for file in logs:
        print(file)
        with open(file, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.read() 
            custom_log(f"call-id:{callid}", logging.INFO)
            #print(f"call-id:{callid}")
            # 提取 SIP 报文
            sips = {}
            sip_messages = extract_sip_messages_masip(lines, callid)
            #print(sip_messages)
            if callid not in sips:
                sips[callid] = []
            sips[callid] = sip_messages 
            #print(sip_messages)

        return sips
    
def sip_dialog(legs_chans_ips, logs):
  
    ues = {}
    for file in logs:
        print(file)
        with open(file, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.read()
            print(legs_chans_ips)
            if len(legs_chans_ips) == 0:
                return
        
            legs = legs_chans_ips.keys()

            print(legs)
            for leg in legs:
                pattern_a = rf"[2].*for CallLeg\[{leg}]\swith Call-ID:\s(.+?)\."
                matches = re.finditer(pattern_a, lines)
                for match in matches:
                    # print(match.group())
                    c = match.group().split()[-1]
                    if leg not in ues:
                        ues[leg] = set()
                    ues[leg].add(c[:-1] if c.endswith('.') else c)

            if len(ues) > 0:
                for callid in ues.values():
                    callid = ''.join(callid)

                    custom_log(f"call-id:{callid}", logging.INFO)
                    print(f"call-id:{callid}")
                    # 提取 SIP 报文
                    sips = {}
                    sip_messages = extract_sip_messages(lines, callid)
                    if callid not in sips:
                        sips[callid] = []
                    sips[callid] = sip_messages

                return sips
            # 选出2条必要的callid
            # for leg in legs:
                # for ips in legs_chans_ips[leg].values():
                # for ip in ips:

                # for message in sip_messages:
                #     print(message)


class Agent:
    def __init__(self, uid, phone):
        self.uid = uid
        self.phone = phone


class Customer:
    def __init__(self, phone):
        self.phone = phone


def agent_event(obj, logs):
    if obj is None:
        print("没有座席")
        return 0
    print("\n座席分析...")
    record_file = ""
    for callid in obj:
        print(callid)
        messages = obj[callid]

        i = 0
        for line in messages.splitlines():
            if i == 0:
                if "recv from" in line:
                    print("呼入电话<------------")
                elif "send to" in line:
                    print("外呼-------------->")
            elif i > 0:
                if "recv from" in line:
                    print("<------------")
                elif "send to" in line:
                    print("-------------->")

    return 0
    for file in logs:
        f = obj.record_name[0:-4]

        pattern = rf"recNotify\(\"REC:.*{f}"
        # grep -E "Call\[40\].*wav"  log/rec\(114867\)0722T14_01.log

        # 2023-07-22 14:23:05.787 115044 I CM Call[40] record to record/2023-07-22/34699/0040142305786.wav
        agent = ""
        with open(file, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.read()  # 读取所有内容
            matches = re.finditer(pattern, lines)  # 迭代匹配结果
            for match in matches:

                # 使用正则表达式提取手机号码
                pattern = r'REC:(\d+)'
                matches = re.findall(pattern, match.group())
                if matches:
                    phone_number = matches[0]
                    # print("Phone number:", phone_number)
                    customer = Customer(phone_number)
                    obj.customer = customer
            agent_phone = ""
            if obj.customer:

                # USR[_0KE3R68EBHR3QVJCS6T3GINUG].usrDo("startPlay$MV7ONU", "startPlay"
                pattern2 = rf"IPCC30\sroute.*{obj.customer.phone}.*flags"
                # print(pattern2)
                matches = re.finditer(pattern2, lines)  # 迭代匹配结果
                for match in matches:
                    print(obj.direction, match.group())
                    # 使用正则表达式提取数字
                    pattern = rf'IPCC30\sroute\s{obj.customer.phone}.*\s+(\d+)\s+flags'
                    matches = re.search(pattern, match.group())

                    if matches:
                        agent_phone = matches.group(1)
                        print("agnet no:", agent_phone)
            if agent_phone:
                # 匹配包含关键字 "6041" 的行
                pattern = rf'.*{agent_phone}.*'
                include_calls = []
                for line in lines.splitlines():
                    if re.match(pattern, line):
                        include_calls.append(line)
                # 提取 "USR[]" 括号中的内容
                usr_list = []
                for line in include_calls:
                    match = re.search(r'USR\[(.*?)\]', line)
                    if match:
                        usr_list.append(match.group(1))
                # 统计去重并找到出现次数最多的USR[]
                counter = Counter(usr_list)
                most_common = counter.most_common(1)

                obj.agent = Agent(most_common[0][0], agent_phone)


def clear():
    os.system('cls')


def main():
    clear()
    custom_log(A_VERY_LONG_LINE, logging.INFO)
    parser = argparse.ArgumentParser(description='提供一个手机号码或者录音文件名 ... ')
    parser.add_argument('phone_number', type=str, nargs='+',
                        help='待分析的号码或者录音文件名（多个号码之间用逗号分隔）。')
    parser.add_argument('-P', '--path', type=str, default=0,
                        help='指定日志目录，默认搜索当前目录下的日志')
    parser.add_argument('-D', '--debug', type=int, default=0,
                        help='指定分析日志的级别，0-4级，默认0关闭详情模式')
    parser.add_argument("-B", "--bug_test", action="store_true",
                        help="排查模式,默认不启用。")
    parser.add_argument("-A", "--agent_id", type=str, default=0,
                        help='座席工号')
    if len(sys.argv) < 2:
        parser.print_help()
        custom_log(A_VERY_LONG_LINE, logging.INFO)
        return

    args = parser.parse_args()

    # 将文件名参数存储在一个列表中
    phone_numbers = []
    for name in args.phone_number:
        phone_numbers += name.split(',')

    # 可以使用 len() 来获取文件名的数量
    num_of_files = len(phone_numbers)

    # 获取可选参数的值
    input_path = args.path
    input_debug = args.debug
    input_test = args.bug_test
    if input_path == 0:
        input_path = os.getcwd()
        
    print("Files to process: ", phone_numbers)
    print("Number of files: ", num_of_files)
    print("log path : ", input_path)
    print("bug detect : ", input_test)
    i_name = 0
    clear()

    custom_log("----------------------AnalyzeNow.", logging.WARNING)
    for phone_name in phone_numbers:
        i_name = i_name + 1
        isRecordFile = False
        if "wav" in phone_name:
            isRecordFile = True
            print(f'[%d] - 分析录音文件:{phone_name}' % i_name)
        else:
            print(f'[%d] - 分析号码:{phone_name}' % i_name)
        pic_name = f'{i_name}-{phone_name}'
        search_dir = "./"
        prepared_log_files = []
        print(input_path)
        
        if "@" in input_path:
            log_path = input_path
            # 分解出用户名、服务器地址、路径和文件名  
            user, server, path, filename = log_path.split('@')[0], log_path.split('@')[1].split(':')[0], log_path.split(':')[1], log_path.split('/')[-1]  
            password = 'haolaos'  # 默认密码  
            # 创建SSH客户端  
            ssh = paramiko.SSHClient()  
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())  
            try:  
                ssh.connect(server, username=user, password=password)  
                # 打开远程文件并读取内容  
                sftp = ssh.open_sftp()  
                with sftp.open(path + '/' + filename, 'r') as f:  
                    log_content = f.read()  
                sftp.close()  
                ssh.close()  
                return log_content  
            except Exception as e:  
                print(f"Error: {e}")  
        elif os.path.isdir(input_path):
            for root, dirs, files in os.walk(input_path):
                for file in files:
                    if ('rec' in file or 'sbc' in file) and file.endswith('.log'):
                        prepared_log_files.append(os.path.join(root, file))
        elif os.path.isfile(input_path):
            prepared_log_files.append(input_path)
        else:
            for root, dirs, files in os.walk(search_dir):
                for file in files:
                    if ('rec' in file or 'sbc' in file) and file.endswith('.log'):
                        prepared_log_files.append(os.path.join(root, file))
        matched_logs = []
        for file in prepared_log_files:
            with open(file, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
                for line in lines:
                    if phone_name in line:
                        matched_logs.append(file)
                        break
        # custom_log(f"确定日志范围：{matched_logs}")
        if len(matched_logs) == 0:
            custom_log("没有找到匹配的日志.", logging.ERROR)
            return
        '''
        - 1.确定日志范围，后面分析都基于这个日志范围，避免全局搜索 -logs
        - 2.列出有效通话，如果号码命中多个通话，让用户选择分析哪一通；后面分析都基于这个 - obj选择
        - 3.提取录音/通话开始-结束
        - 4.丢包统计 ,分析RTP CallLeg
        - 5.终端分析 ,识别通话使用的话机型号,终端型号,IP:PORT
        - 6.座席分析, 在接待客户期间,座席执行了哪些指令
        '''
        print(f"\n-1.确定日志范围...")
        # print(matched_logs)
        custom_log(f"{matched_logs}", logging.INFO)

        # `A if condition else B`
        print("\n-2.列出有效通话...")
        selectItem = None
        call, call_legs = chooseOneCall(phone_name, matched_logs)
        # print("get:", selectItem)

        if selectItem is None:
            # direction = selectItem.get_direction()
            # call_direction = "外呼:" if direction == 1 else "呼入:"
            # 分析录音开始和结束时间
            print("\n-3.提取录音...")
            tapeObj = duration_cal(call, matched_logs)

            print("\n-4.丢包统计...")
            legs_chans_ips = None
            if len(call_legs) > 1 :
                legs_chans_ips = rtp_count(call_legs, matched_logs)

            print("\n-5.SIP分析...")
            sips = None
            if  legs_chans_ips is not None:
                sips = sip_dialog(legs_chans_ips, matched_logs, input_path)
            elif call and len(call_legs) > 0 :
                sips = sip_masip(call, matched_logs)
            # selectItem.showConnection()
            
            print("\0.分析AGENT")

            agent_event(sips, matched_logs)

            custom_log("----------------------TheEnd.", logging.WARNING)
            print("\n")
            # print("2.分析右侧sip")
            # print("3.分析右侧丢包")
            # selected_number = get_valid_input(4)

            # 继续执行其他业务
            # if selected_number is not None:
            #     print(f"您选择的对象是：{selected_number}")


if __name__ == "__main__":
    main()
