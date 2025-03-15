import requests
import json
import time
import os

'''
初始数据
sleep_time  刷新时间  单位秒
roomid 房间地址
部分直播间不是真实地址
点一下分享直播间可以看到不一样的房间地址
'''
sleep_time = int(input('刷新时间(单位秒)='))
print('部分直播间不是真实地址\n点一下分享直播间可以看到不一样的房间地址')
roomid = input('房间号=')
url = "https://api.live.bilibili.com/xlive/web-room/v1/dM/gethistory?roomid="+roomid


'''
用来显示弹幕
可以添加分支函数 来做一个 功能选择  
是否显示时间  是否显示用户名等  
'''
def show(danmulist):
    for i in range (len(danmulist)):
        print('{0} : {1} ----{2}'.format(danmulist[i]['nickname'],danmulist[i]['text'],danmulist[i]['timeline']))
''' 
初始化
获得第一次弹幕历史
'''
r = requests.get(url)
message = json.loads(r.text)
danmu_new = []
danmu = []
danmuhistory = []
danmu = message['data']['room']
if len(danmu)>0:
    danmuhistory += danmu
    show(danmuhistory)

while True:

    r = requests.get(url)
    message = json.loads(r.text)

    os.system("cls")

    danmu_new = message['data']['room']
    '''
    防止弹幕历史为空 索引超出报错
    '''
    if len(danmuhistory)==0:
        if len(danmu_new)==1:
            danmuhistory += danmu_new
            show(danmuhistory)
        time.sleep(sleep_time)
        continue
    '''
    通过对比两次获取的弹幕的时间 来判断是否重复
    将不重复的内容添加到显示列表里
    '''
    if danmu_new[-1]["timeline"] == danmuhistory[-1]["timeline"] :
        pass
    elif danmu_new[-1]["text"] == danmuhistory[-1]["text"] and danmu_new[-1]["nickname"] == danmuhistory[-1]["nickname"]:
        pass
    else:
        for i in range(len(danmu_new)):
            '''
            每次获取的弹幕 有房管和普通弹幕 各10条
            这边是检查出重复的是哪个位置
            将这个位置后的添加到显示列表中
            '''
            if danmuhistory[-1]["timeline"] == danmu_new[i]["timeline"] and danmuhistory[-1]["text"] == danmu_new[i]["text"] and danmuhistory[-1]["nickname"] == danmu_new[i]["nickname"]:
                # print(danmu_new[i]["timeline"])
                danmuhistory += danmu_new[i+1:]   
                
    show(danmuhistory)
        
    time.sleep(sleep_time)
