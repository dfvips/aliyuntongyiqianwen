import uuid
import requests
import threading
import time
import json
import copy
import userinfo
import sys
import logging
from logging.handlers import RotatingFileHandler

# 定时器开关
# is_running = True
timer_thread = None

# 停止事件
stop_event = threading.Event()

# 请求头
headers = {
    'accept': 'application/json,text/plain,*/*',
    'accept-language': 'zh-CN,zh;q=0.9',
    'content-type': 'application/json',
    'origin': 'https://qianwen.aliyun.com',
    'referer': 'https://qianwen.aliyun.com/chat',
    'sec-ch-ua': '\\"MicrosoftEdge\\";v=\\"111\\",\\"Not(A:Brand\\";v=\\"8\\",\\"Chromium\\";v=\\"111\\"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'user-agent': 'Mozilla/5.0(Macintosh;IntelMacOSX10_15_7)AppleWebKit/537.36(KHTML,likeGecko)Chrome/113.0.0.0Safari/537.36',
    'x-xsrf-token': userinfo.token, # token
    'cookie': userinfo.cookie # cookie
}

# 心跳
def heartbeat():
    api = requests.get('https://qianwen.aliyun.com/heartbeat?type=1&', headers=headers)
    log('\n心跳：' + str(api.status_code))
    pass

# 心跳定时器
def timer():
    while not stop_event.is_set():
        # 定时执行的操作
        heartbeat()
        # 等待停止事件，设置适当的超时时间
        stop_event.wait(timeout=5)

def log(data):
    # 配置日志记录
    log_formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
    log_handler = RotatingFileHandler(filename='app.log', maxBytes=1024*1024*1024, backupCount=3)
    log_handler.setFormatter(log_formatter)
    logging.basicConfig(level=logging.INFO, handlers=[log_handler])

    # 日志记录
    logging.info(data)


# 添加会话凭证
def addSession(q):
    data = senReq('https://qianwen.aliyun.com/addSession', {
        'firstQuery': q
    }, headers)
    if len(data) != 0:
        # userId = data['userId'] # 这里是userId
        # sessionId = data['sessionId'] # 这里是sessionId
        # print('当前会话%s: %s'% (sessionId, q))
        print('当前会话:' + q)
        return data
    else:
        return {}

def querySessionList():
    data = senReq('https://qianwen.aliyun.com/querySessionList', {}, headers)
    if isinstance(data, list) and len(data) != 0:
        # 遍历列表
        for index, item in enumerate(data):
            # 获取该元素中的对应键值
            # userId = item['userId'] # 这里是userId
            # sessionId = item['sessionId'] # 这里是sessionId
            summary = item['summary'] # 提问的问题
            # print('UserID：%s\tSessonID：%s\tSessonName：%s'% (userId,sessionId,summary))
            print('历史会话%s: %s'% (index + 1, summary))
        return data
    else:
        print('当前为初始会话')
        return {}

# 获取上一个问题信息
def getParentMsg(s):
    data = senReq('https://qianwen.aliyun.com/queryMessageList', {
        'sessionId': s
    }, headers)
    try:
        if isinstance(data, list) and len(data) != 0:
            # 遍历列表
            message = data[0] # 获取最新一条消息
            msgId = message['msgId'] # 获取消息id
            return msgId
        else:
            info = '当前为会话的初始的聊天'
            print(info)
            log(info)
            return 0
    except:
        return 0    

# 聊天
def chat(q, pId, sId, ifSearch):
    chat_header = copy.copy(headers) 
    chat_header['accept'] = 'text/event-stream' # 启用时间流
    msgId = str(uuid.uuid4()).replace('-', '') # 生成新消息Id
    data = {
        'action': 'next',
        'msgId': msgId,
        'parentMsgId': pId,
        'contents': [
            {
                'contentType': 'text',
                'content': q
            }
        ],
        'openSearch': ifSearch,
        'sessionId': sId,
        'model': ''
    } 
    # 创建消息体
    payload = json.dumps(data)
    response = requests.request('POST', 'https://qianwen.aliyun.com/conversation', headers=chat_header, data=payload, stream=True)
    previous_content = ''
    for line in response.iter_lines(decode_unicode=True):
        if line:
            stripped_line = line.replace('data:', '')
            try:
                data = json.loads(stripped_line)
                content = data['content'][0]
                # 去除已经包含在前一条数据中的部分
                if content.startswith(previous_content):
                    content = content.replace(previous_content, '', 1).strip()

                for char in content:
                    sys.stdout.write(char)
                    log(char)
                    sys.stdout.flush()
                    time.sleep(0.01)  # 添加适当的延迟
                previous_content = data['content'][0]# 更新前一条数据
            except json.decoder.JSONDecodeError as e:
                log(e.msg)
                pass
# 发送请求
def senReq(url, data, headers):
    payload = json.dumps(data)
    response = requests.request('POST', url, headers=headers, data=payload)
    if isJson(response.text):
        res_data = response.json()
        if res_data['success']:
            data = res_data['data']
            return data
        else:
            info = '请求接口出错了'
            print(info)
            log(info)
            return {}
    else:
        info = '登录信息异常，请重新更新登录数据'
        print(info)
        log(info)
        return {}

# 判断是否Json数据，如果是Html说明登录信息异常
def isJson(str):
    try:
        data = json.loads(str)
        log(data)
    except ValueError:
        return False
    return True

# 请用户选择会话
def getSessionIndex(array):
    user_input = ''
    while True:
        user_input = input("请选择会话的序号[1-{}]: ".format(len(array)))
        try:
            user_num = int(user_input)
            if user_num > 0 and user_num < len(array):
                break
            else:
                print("数字必须大于0且小于{}！".format(len(array)))
        except ValueError:
            print("无效的输入，请输入一个数字！")
    return user_input    

# 请用户选择是否载入历史会话
def checkIfLoadSession():
    # 提示是否载入上次的会话
    sId = 0
    while True:
        answer = input("是否载入上次的会话？(Y/N): ")
        if answer.upper() == "Y":
            sessionData = querySessionList()
            if len(sessionData) > 0:
                s = getSessionIndex(sessionData)
                sId = sessionData[int(s) - 1]['sessionId']
            break
        elif answer.upper() == "N":
            break
        else:
            print("请输入正确的选项！")
    return sId        

# 请用户选择是否开启搜索
def checkIfSearch():
    ans = False
    while True:
        answer = input("是否开启搜索模式？(Y/N): ")
        if answer.upper() == "Y":
            ans = True
            break
        elif answer.upper() == "N":
            break
        else:
            print("请输入正确的选项！")
    return ans   

def quit():
    # global is_running
    # is_running = False
    print("\n感谢您使用通义千问，欢迎再次使用！")    
    stop_event.set()

# Main入口
if __name__ == '__main__':
    try:
        timer_thread = threading.Thread(target=timer)
        timer_thread.start()
        # 固定回复，不发起请求
        print('我是来自达摩院的大规模语言模型，我叫通义千问。我是达摩院自主研发的超大规模语言模型，也能够回答问题、创作文字，还能表达观点、撰写代码。如果您有任何问题或需要帮助，请随时告诉我，我会尽力提供支持。')
        sId = checkIfLoadSession() # 获取会话Id
        ifSearch = checkIfSearch() # 检查搜索模式
        while True:
            q = input('\r\n输入您的问题：') # 提取问题
            if q != 'exit': 
                if(sId == 0):
                    sessionData = addSession(q) # 如果没有会话，则加入会话
                    sId = sessionData['sessionId']
                lastChatId = getParentMsg(sId) # 获取上一条消息的id
                chat(q, lastChatId,sId,ifSearch) # 发送消息
            else:
                break  
        quit()
    except KeyboardInterrupt:
        quit()
