#!/usr/bin/python
# -*- coding: UTF-8 -*-
import datetime
import re
import os
import subprocess
import sys
import argparse
import matplotlib.pyplot as plt
import numpy as np
import matplotlib as mpl
import json

DEBUG = 5


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


def printInfo(line):
    if DEBUG > 3:
        print("\033[32m{}\033[0m".format(line.strip()))


def printNormal(line):
    if DEBUG > 2:
        print("\033[37m{}\033[0m".format(line.strip()))


def printDebug(line):
    if DEBUG > 1:
        print("\033[36m{}\033[0m".format(line.strip()))


def printWarn(line):
    if DEBUG > 0:
        print("\033[33m{}\033[0m".format(line.strip()))


def printError(line):
    print("\033[31m{}\033[0m".format(line.strip()))


def get_address_from_callleg(line, num):
    pattern = r"CallLeg\[" + str(num) + "\] from\s(.+?)\sto\s(.+?)\s"
    match = re.search(pattern, line)
    if match:
        from_address = match.group(1).split("<")[1][:-1]  # 提取from地址，并去除"<>"
        to_address = match.group(2)
        address_str = "CallLeg[{}] from {} to {}".format(
            num, from_address, to_address)
        return address_str
    else:
        return None


def mp4files():
    # 运行shell命令
    # grep -E "videoRecord.*mp4" room* | cut -d" " -f9 | cut -d"/" -f7 | tr "\r" "," | tr "\n" " "
    p1 = subprocess.Popen(["grep -E 'videoRecord.*mp4' room*"],
                          stdout=subprocess.PIPE, shell=True)
    p2 = subprocess.Popen(["cut -d' ' -f9"], stdin=p1.stdout,
                          stdout=subprocess.PIPE, shell=True)
    p3 = subprocess.Popen(["cut -d'/' -f7"], stdin=p2.stdout,
                          stdout=subprocess.PIPE, shell=True)
    p4 = subprocess.Popen(["tr '\\r' ','"], stdin=p3.stdout,
                          stdout=subprocess.PIPE, shell=True)
    output, _ = p4.communicate()

    # 处理命令输出
    output = re.sub(b'\n', b' ', output)
    output = output.decode('utf-8')

    return output


def allmp4files():

    log_files = [file for file in os.listdir() if file.startswith("room")]

    dict = {}
    result = []
    pattern = r"videoRecord to .*?/(.*?)\.mp4"
    skip_zero_filenames = []
    for file in log_files:
        with open(file, "r", encoding='utf-8', errors='replace') as f:
            for line in f:
                match = re.search(pattern, line)

                if match:
                    mp4f = match.group(1).split('/')[-1] + ".mp4"
                    result.append(mp4f)
                elif len(line) < 150:
                    continue
                elif 'content = ' in line:
                    # 提取 JSON 串
                    start = line.find('content = ') + len('content = ')
                    end = line.rfind('}')
                    json_str = line[start:end+1]

                    # 解析 JSON 对象
                    data = json.loads(json_str)

                    try:
                        succ = data['result']
                    except:
                        continue

                    if not succ:
                        continue
                    if len(data) < 5:
                        continue

                    try:
                        # 解析 "contract_info" 的 value 部分
                        contract_info = json.loads(
                            data['appData']['contract_info'])
                        filename = data['file'].split('/')[-1].strip()
                        roomid = contract_info['roomId'].strip()
                        duration = data['duration']
                    except KeyError:
                        # print("JSON中不存在'roomId'键")
                        continue

                    if duration == 0:
                        skip_zero_filenames.append(filename)
                        continue

                    if not is_filename_numeric(filename):
                        # print(filename, is_filename_numeric(filename))
                        continue
                    dict[filename] = roomid
                    # result.append(data['file'])

    if len(dict) > 0:
        printWarn("单向视频要选择roomId分析~~")
        print(dict)
    if len(result) > 0:
        printWarn("双向视频直接选择文件名分析~~")
        result_str = ",".join(result)
        printInfo(result_str)
    if len(skip_zero_filenames) > 0:
        printWarn(f"跳过时长为0的录像:{skip_zero_filenames}")


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


def main():
    parser = argparse.ArgumentParser(description='Process some files.')
    parser.add_argument('filename', metavar='N', type=str, nargs='+',
                        help='file name(s) to be processed')
    parser.add_argument('-S', '--size', metavar='S', type=int, default=0,
                        help='the size of the input to be processed (default: 0)')
    parser.add_argument('-s', '--lost', metavar='s', type=int, default=50,
                        help='the lost of the input to be processed (default: 0)')
    parser.add_argument('-z', '--ratio', metavar='s', type=int, default=0,
                        help='the ratio of lost packets (default: 0)')
    parser.add_argument('-D', '--debug', metavar='E', type=int, default=0,
                        help='the debug level 0 ~ 4 to be printed (default: 0)')
    parser.add_argument("-B", "--bug_test", action="store_true",
                        help="启用 bug_test 参数")

    parser.add_argument('-r', '--reverse', metavar='E', type=int, default=False,
                        help='the plot ordered revered. (default: 0)')
    if len(sys.argv) <= 2:
        parser.print_help()
        print('\n---guests:')
        allmp4files()
        exit

    args = parser.parse_args()

    # 将文件名参数存储在一个列表中
    callids_to_process = []
    for name in args.filename:
        callids_to_process += name.split(',')
    # files_to_process = args.filename

    # 可以使用 len() 来获取文件名的数量
    num_of_files = len(callids_to_process)

    # 获取可选参数的值
    input_size = args.size
    input_lost = args.lost
    input_ratio = args.ratio
    input_debug = args.debug
    input_revered = args.reverse
    input_revered = args.reverse
    input_bug_test = args.bug_test

    print("Files to process: ", callids_to_process)
    print("Number of files: ", num_of_files)
    i_name = 0

    for callid_name in callids_to_process:
        i_name = i_name + 1
        isRoomId = False
        if len(callid_name) > 30 and "mp4" not in callid_name:
            isRoomId = True
        if isRoomId:
            print(f'[%d] - 分析roomId:{callid_name}' % i_name)
        else:
            print(f'[%d] - 分析Call-ID:{callid_name}' % i_name)
        pic_name = f'{i_name}-{callid_name}'
        leg_revered = False
        if input_revered:
            leg_revered = input_revered

        prepared_log_files = []
        for root, dirs, files in os.walk("./"):
            for file in files:
                if '(' in file and 'T' in file and file.endswith('.log'):
                    prepared_log_files.append(os.path.join(root, file))

        matched_logs = []
        for file in prepared_log_files:
            with open(file, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
                for line in lines:
                    if callid_name in line:
                        matched_logs.append(file)
                        break
        printDebug(f"在以下日志文件中匹配到了录像文件名相关内容：\n{matched_logs}")
        call_leg = ""
        call_number = ""
        signleVideo = ""
        for file in matched_logs:
            if f"room" in file:
                # video
                startFind = False
                linenumber = 0
                c = ""
                audio = ""
                video = ""

                with open(file, 'r', encoding='utf-8', errors='replace') as f:
                    lines = f.readlines()
                    for line in lines:
                        if isRoomId and f"INVITE sip:9*{callid_name}" in line:
                            startFind = True
                        elif startFind and isRoomId and linenumber < 40:
                            linenumber = linenumber + 1
                            if f"c=IN IP4 " in line:
                                c = line.split()[2].strip()
                            if f"m=audio " in line:
                                audio = line.split()[1].strip()
                            if f"m=video " in line:
                                video = line.split()[1].strip()
                            if c and audio and video:
                                signleVideo = Connection(c, audio, video)
                                break
                        elif startFind and isRoomId and linenumber > 40:
                            startFind = False
                            linenumber = 0
                        elif "Call" in line and "videoRecord" in line and callid_name in line:
                            call_number = line.split("[")[1].split("]")[0]

                            break
            if f"sbc" in file:
                with open(file, 'r', encoding='utf-8', errors='replace') as f:
                    lines = f.readlines()
                    if not call_leg:
                        for line in lines:
                            if "CallLeg" in line and "with Call-ID" in line and callid_name in line:
                                call_leg = line.split("[")[1].split("]")[0]
                                print(call_leg)
                                break
                    if not call_number:
                        for line in lines:
                            if f"add CallLeg[{call_leg}], it is" in line:
                                call_number = line.split("[")[1].split("]")[0]
            if signleVideo:
                break
            if call_number:
                break
        if isRoomId:
            pass
        elif call_number:
            printInfo(f"在日志中匹配到了Call number：{call_number}")
        else:
            printError('没有找到关联的call')
            continue

        call_leg_0 = ""
        call_leg_1 = ""
        for file in matched_logs:
            with open(file, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
                callleg_0_callid = ""
                callleg_1_callid = ""

                for line in lines:
                    if f"Call[{call_number}] add CallLeg[" in line:
                        if "Initiator" in line:
                            call_leg_0 = line.split("[")[2].split("]")[0]
                        elif "Acceptor" in line:
                            call_leg_1 = line.split("[")[2].split("]")[0]
                        # 2023-05-25 22:34:42.350 008190 I RT append Dialog(0xe52d1380) for
                        # CallLeg[652] with Call-ID: NmQ4OTMwNzI0ODE5ZmE5NmEyY2UwNjc1ZDkzMTNiODI.
                    if call_leg_0 and f"CallLeg[{call_leg_0}] with Call-ID" in line:
                        callleg_0_callid = line.split(":")[3]
                    elif call_leg_1 and f"CallLeg[{call_leg_1}] with Call-ID:" in line:
                        callleg_1_callid = line.split(":")[3]

                if callleg_0_callid and callleg_1_callid:
                    # if "mp4" in callid_name:
                    #     printInfo(
                    #         f"在日志中匹配到了Phone call-id：{call_leg_0} Call-ID={callleg_0_callid} ")
                    # elif callid_name == callleg_0_callid:
                    #     printInfo(
                    #         f"在日志中匹配到了Phone call-id：{call_leg_0} Call-ID={callleg_0_callid} ")
                    # else:
                    printInfo(
                        f"{call_leg_0} Call-ID={callleg_0_callid}{call_leg_1} Call-ID={callleg_1_callid} ")
                    break
        if isRoomId:
            pass
        elif call_leg_0 and call_leg_1:
            printInfo(f"在日志中匹配到了CallLeg numbers：{call_leg_0}, {call_leg_1}")
        else:
            printError('没有找到关联的call leg')
            exit()

        call_leg_0_channel_0 = ""
        call_leg_0_channel_1 = ""
        call_leg_1_channel_0 = ""
        call_leg_1_channel_1 = ""

        cha_of_conn = {}

        for file in matched_logs:
            with open(file, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
                for line in lines:
                    address = None
                    if isRoomId and f"peer address is {signleVideo.audioConn()}" in line:
                        call_leg_0_channel_0 = line.split(
                            "[")[1].split("]")[0]
                        print("人机音频端口:", signleVideo.audioConn(),
                              call_leg_0_channel_0)
                        cha_of_conn[call_leg_0_channel_0] = {
                            'name': '音频', 'conn': signleVideo.audioConn()}
                    elif isRoomId and f"peer address is {signleVideo.videoConn()}" in line:
                        call_leg_0_channel_1 = line.split(
                            "[")[1].split("]")[0]
                        print("人机视频端口:", signleVideo.videoConn(),
                              call_leg_0_channel_1)
                        cha_of_conn[call_leg_0_channel_1] = {
                            'name': '音频', 'conn': signleVideo.videoConn()}
                    if isRoomId and call_leg_0_channel_0 and call_leg_0_channel_1:
                        print(call_leg_0_channel_0, call_leg_0_channel_1)

                        break

                    if "CallLeg[{}]".format(call_leg_0) in line:
                        address = get_address_from_callleg(line, call_leg_0)
                    elif "CallLeg[{}]".format(call_leg_1) in line:
                        address = get_address_from_callleg(line, call_leg_1)
                    if address:
                        print(address)

                    if f"CallLeg[{call_leg_0}] set CallLegChannel[" in line:
                        if call_leg_0_channel_0 == "":
                            call_leg_0_channel_0 = line.split(
                                "[")[2].split("]")[0]
                        elif call_leg_0_channel_1 == "":
                            call_leg_0_channel_1 = line.split(
                                "[")[2].split("]")[0]
                    elif f"CallLeg[{call_leg_1}] set CallLegChannel[" in line:
                        if call_leg_1_channel_0 == "":
                            call_leg_1_channel_0 = line.split(
                                "[")[2].split("]")[0]
                        elif call_leg_1_channel_1 == "":
                            call_leg_1_channel_1 = line.split(
                                "[")[2].split("]")[0]
                    if call_leg_0_channel_0 and call_leg_0_channel_1 and call_leg_1_channel_0 and call_leg_1_channel_1:
                        break
            if call_leg_0_channel_0 and call_leg_0_channel_1 and call_leg_1_channel_0 and call_leg_1_channel_1:
                break

        if isRoomId:
            pass
        elif call_leg_0_channel_0 and call_leg_0_channel_1:
            printInfo(
                f"在日志中匹配到了CallLegChannel Left：{call_leg_0_channel_0}, {call_leg_0_channel_1}")
        else:
            printError('left 没有找到关联的call leg Channel.')
            exit()

        if isRoomId:
            pass
        elif call_leg_1_channel_0 and call_leg_1_channel_1:
            printInfo(
                f"在日志中匹配到了CallLegChannel Rigth：{call_leg_1_channel_0}, {call_leg_1_channel_1}")
        else:
            printError('right 没有找到关联的call leg Channel.')
            exit()

        rtp_stats = []
        no_rtp_chan = []
        statistics = "Statistics"
        if input_debug > 0:
            statistics = ""

        for file in matched_logs:
            with open(file, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
                for line in lines:
                    if f"MediaChannel[{call_leg_0_channel_0}] RTP {statistics}" in line:
                        rtp_stats.append(line)
                    elif f"MediaChannel[{call_leg_0_channel_1}] RTP {statistics}" in line:
                        rtp_stats.append(line)
                    elif f"MediaChannel[{call_leg_1_channel_0}] RTP {statistics}" in line:
                        rtp_stats.append(line)
                    elif f"MediaChannel[{call_leg_1_channel_1}] RTP {statistics}" in line:
                        rtp_stats.append(line)
        data = []
        for line in rtp_stats:
            match = re.search(r"RTP Statistics: (\d+)/(\d+)", line)
            if match:
                numerator = int(match.group(1))
                denominator = int(match.group(2))
                r = int((numerator) * 100 / denominator)

                if (input_ratio > 0) and (r > input_ratio):
                    no_rtp_chan.append(line.split("[")[1].split("]")[0])
                    printError(
                        f"{r}% is horrible: {line}")
                elif (input_lost > 0) and (numerator > input_lost):
                    no_rtp_chan.append(line.split("[")[1].split("]")[0])
                    printWarn(
                        f"{numerator} > {input_lost}: {line}")
                elif (input_size > 0) and (denominator <= input_size):
                    no_rtp_chan.append(line.split("[")[1].split("]")[0])
                    printWarn(f"{denominator} < {input_size}: {line}")
                else:
                    printNormal(line)
            elif "no rtp received" in line:
                printWarn(f"{line}")
                no_rtp_chan.append(line.split("[")[1].split("]")[0])
            elif input_debug > 1 and f" RTP Instant" in line:
                if 1:
                    time = line.split(' ')[1]
                    channel = line.split(' ')[5]
                    lost = line.split(' ')[9]
                    data.append(f'{time} {channel} {lost}')
                    if DEBUG >= 5:
                        printInfo(f'{time} {channel} {lost}')
                else:
                    match = re.match(
                        r'^(.*?) (.*?) D CM (MediaChannel\[\d+\]) RTP Instant: lost: (\d+)/(\d+),', line)
                    if match:
                        if len(match.group(1).split(' ')) > 1:
                            time = match.group(1).split(' ')[0]
                            channel = match.group(3)
                            lost = match.group(4) + '/' + match.group(5)
                            data.append(f'{time} {channel} {lost}')
                            print(f'{time} {channel} {lost}')

            else:
                printWarn(line)

        # 打印丢包通道对应的地址端口
        local_addresses = {}
        video_addresses = []
        for file in matched_logs:
            with open(file, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
                for line in lines:
                    for chan in no_rtp_chan:
                        if f"MediaChannel[{chan}] initialized, local address is" in line:
                            m = re.search(
                                r"local address is (\d+\.\d+\.\d+\.\d+):(\d+)", line)
                            n = re.search(
                                r"peer address is (\d+\.\d+\.\d+\.\d+):(\d+)", line)
                            if m and n:
                                if chan not in local_addresses:
                                    print(cha_of_conn[chan]
                                          ['name'], "网络连接上存在丢包")

                                    local_addresses[chan] = [
                                        (m.group(0), n.group(0))]
                                    printError(
                                        f'MediaChannel[{chan}]: {m.group(0)}<----{ n.group(0)}')
                                    video_addresses.append(
                                        f'MediaChannel[{chan}]:{ n.group(0).replace("peer address is","From:")} ---> {m.group(0).replace("local address is","To:")}')
        if input_debug == 2:
            a = MediaChannelPlotter(data,  False, True)
            if 0 == a.plot(pic_name,  video_addresses):
                print(f"\n save {callid_name}.png 保存成功.")
        elif input_debug == 3:
            a = MediaChannelPlotter(data,  False, True)
            callid_name = f'{callid_name}-limit'
            if 0 == a.plot_new(callid_name,  video_addresses):
                print(f"\n save {callid_name}.png 保存成功.")
    if input_bug_test:
        # 如果启用了 -B 参数
        # 执行相关的代码
        print("启用了 bug_test 参数")
        for file in matched_logs:
            if f"room" in file:
                # video
                with open(file, 'r', encoding='utf-8', errors='replace') as f:
                    lines = f.readlines()
                    for line in lines:
                        # bug ffmpeg-24
                        if "Buffer queue overflow" in line:
                            printError(line)
                            break


if __name__ == "__main__":
    main()
