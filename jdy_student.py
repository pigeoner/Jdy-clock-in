#!/usr/bin/env python
# -*- coding:utf-8 -*-
# Copyright (c) 2021 pigeoner All rights reserved.
# 简道云自动打卡脚本（学生版）
# 第一次运行需要将settings_default.yaml复制一份到本地，
# 并将其重命名settings.yaml，
# 然后根据提示填写配置信息，
# 第一次运行会生成二维码，扫描后自动获取cookie。
# cookie和需要提交的表单信息在第一次运行后
# 会自动保存到同目录的settings.yaml文件内。

import requests
import time
import re
from PIL import Image
import json
import random
import yaml
import os


class Jdy:
    def __init__(self, urls, headers):
        self.urls = urls
        self.headers = headers
        self.key = None
        self.auth_code = None
        self.cookie = None
        self.csrf = None
        self.userInfo = None
        self.appId = None
        self.entryId = None
        self.entryDetails = None

    def get_key(self):

        html = requests.get(self.urls[0], headers=self.headers)
        key = re.search("(?<=\"key\"\:\")(.*?)(?=\")",
                        html.content.decode()).group(1)
        self.key = key
        try:
            del self.headers['Referer']
        except KeyError:
            pass
        return key

    def show_qrcode(self):

        # 访问imgurl，将二维码保存到本地
        res = requests.get(self.urls[1]+self.key, headers=self.headers)
        with open('qrcode.jpg', 'wb') as f:
            f.write(res.content)
        # 暂停2秒，不然加载的二维码可能比较模糊
        time.sleep(2)
        # Pillow读取二维码
        img = Image.open('qrcode.jpg')
        # 在窗口中显示
        img.show()

    def get_auth_code(self):

        timestamp = int(time.time()*1000)
        url = self.urls[2].format(self.key, timestamp)
        html = requests.get(url, headers=self.headers)
        qrcode_response = json.loads(
            re.search('(?<=jsonpCallback\()(.*?)(?=\))', html.text).group(1))
        if qrcode_response['status'] == 'QRCODE_SCAN_SUCC':
            self.auth_code = qrcode_response['auth_code']
            return qrcode_response['auth_code']
        elif qrcode_response['status'] == 'QRCODE_SCAN_ERR':
            print('登录出错.')
            exit(1)
            return None
        else:
            return self.get_auth_code()

    def get_cookie(self):

        url = self.urls[3].format(self.auth_code)
        session = requests.session()
        session.get(url, headers=self.headers)
        cookie = requests.utils.dict_from_cookiejar(session.cookies)
        self.cookie = cookie
        return cookie

    def get_csrf_token(self):

        html = requests.get(
            self.urls[4], headers=self.headers, cookies=self.cookie)
        csrf = re.search(
            'window\.jdy\_csrf\_token ?= ?\"(.*?)\"', html.text).group(1)
        self.csrf = csrf
        self.headers['X-CSRF-Token'] = csrf
        return csrf

    def get_user_info(self):

        html = requests.post(
            self.urls[5], headers=self.headers, cookies=self.cookie)
        # with open('userInfo.json', 'wb') as f:
        #     f.write(html.content)
        self.userInfo = json.loads(html.content.decode('utf8'))
        return html.content

    def get_appId(self):

        html = requests.post(
            self.urls[6], headers=self.headers, cookies=self.cookie)
        res = json.loads(html.content.decode())['apps']
        for e in res:
            if e['name'] == '学生工作部':
                self.appId = e['_id']
                return e['_id']
        return None

    def get_entryId(self):

        url = self.urls[7]+self.appId
        html = requests.post(
            url, headers=self.headers, cookies=self.cookie)
        res = json.loads(html.content.decode())
        entry_id_list = [e['id'] for e in res['entryList']]
        for e in entry_id_list:
            if res['entryMap'][e]['name'] == '学生每日信息填报':
                self.entryId = res['entryMap'][e]['entryId']
                return res['entryMap'][e]['entryId']
        return None

    def get_entry_details(self):

        url = urls[8].format(self.appId, self.entryId)
        html = requests.post(
            url, headers=self.headers, cookies=self.cookie)
        # with open('entryDetails.json', 'wb') as f:
        #     f.write(html.content)
        self.entryDetails = json.loads(html.content.decode('utf8'))
        return html.content

    def generate_settings(self):

        self.get_key()
        self.show_qrcode()
        self.get_auth_code()
        self.get_cookie()
        self.get_csrf_token()
        self.get_user_info()
        self.get_appId()
        self.get_entryId()
        self.get_entry_details()
        self.headers['Content-Type'] = 'application/json;charset=utf-8'

        def get_widget_value(widget_name, cond_0_value):
            for widget in self.entryDetails['entry']['content']['items']:
                if widget['widget']['widgetName'] == widget_name:
                    field = widget['widget']['rely']['data']['field']
                    filter = widget['widget']['rely']['filter']
                    try:
                        del filter['cond'][0]['mode']
                        del filter['cond'][0]['depend']
                    except KeyError:
                        pass
                    filter['cond'][0]['value'] = [cond_0_value]
                    formId = widget['widget']['rely']['data']['formId']
                    break

            payload = {
                'appId': self.appId,
                'entryId': self.entryId,
                'field': field,
                'filter': filter,
                'formId': formId
            }
            res = requests.post(self.urls[9], data=json.dumps(payload),
                                headers=self.headers, cookies=self.cookie)
            value = json.loads(res.content.decode('utf8'))['value']
            return value

        name_id = self.userInfo["memberInfo"]["member_id"]
        stu_no = self.userInfo["memberInfo"]["username"]
        name = self.userInfo["memberInfo"]["nickname"]

        department = get_widget_value('_widget_1581259263911', stu_no)
        major = get_widget_value('_widget_1597408997541', stu_no)
        confirm = department+'-'+stu_no+'-'+name

        xueyuan = get_widget_value(
            '_widget_1599385089556', department)[0]['_id']
        xuegong = get_widget_value(
            '_widget_1599385089589', department)[0]['_id']

        settings = {
            "userInfo": {
                "isFullInfo": 1,
                "cookie": self.cookie,
                "csrf": self.csrf
            },
            "values": {
                "_widget_1581259263912": {
                    "data": name_id,  # 姓名(id)
                    "visible": True
                },
                "_widget_1581325409790": {
                    "data": stu_no,  # 学号
                    "visible": True
                },
                "_widget_1581259263911": {
                    "data": department,  # 学院
                    "visible": True
                },
                "_widget_1597408997541": {
                    "data": major,  # 专业
                    "visible": True
                },
                "_widget_1581259263913": {
                    "data": confirm,  # 填报确认
                    "visible": True
                },
                "_widget_1594972479663": {
                    "data": "北京",  # 目前所在地
                    "visible": True
                },
                "_widget_1597408997159": {
                    "data": "否",  # 该区域是否为中高风险区
                    "visible": True
                },
                "_widget_1595580335402": {
                    "data": "否",  # 以上“目前所在地”勾选选项较昨日是否有变化
                    "visible": True
                },
                "_widget_1595602792466": {
                    "visible": False  # 请填写变动信息
                },
                "_widget_1598020946197": {
                    "visible": False  # 驻地变动前详细地址
                },
                "_widget_1594974441797": {
                    "data": "健康",  # 目前身体健康状况
                    "visible": True
                },
                "_widget_1613443843430": {
                    "visible": False  # 症状情况详细描述
                },
                "_widget_1594974441946": {
                    "data": "否",  # 是否为疑似或确诊
                    "visible": False
                },
                "_widget_1611412944997": {
                    "data": "未隔离",  # 隔离状态
                    "visible": True
                },
                "_widget_1611412945031": {
                    "visible": False  # 隔离地点
                },
                "_widget_1599385089556": {  # 学院抄送
                    "data": [
                        xueyuan
                    ],
                    "visible": False
                },
                "_widget_1599385089589": {  # 学工抄送
                    "data": [
                        xuegong
                    ],
                    "visible": False
                }
            },
            "appId": self.appId,
            "entryId": self.entryId,
            "formId": self.entryId,
            "hasResult": True,
            "authGroupId": -1
        }

        # 修改yaml配置
        with open('settings.yaml', 'r', encoding='utf-8') as f:
            result = f.read()
            yamlInfo = yaml.load(result, Loader=yaml.FullLoader)

            # 修改的值
            settings['values'].update(yamlInfo['values'])
            gaodeUrl = 'https://restapi.amap.com/v3/geocode/geo?key=6f9c62f150c3ed0f69d276eac714e584&address='
            gaodeRes = requests.get(
                gaodeUrl+settings['values']['_widget_1594972480348']['data']['detail'])
            location = json.loads(gaodeRes.text)[
                'geocodes'][0]['location'].split(',')
            location = [float(num) for num in location]
            settings['values']['_widget_1594972480348']['data']['lnglatXY'] = location
            with open('settings.yaml', 'w', encoding='utf-8') as w_f:
                # 覆盖原先的配置文件
                yaml.dump(settings, w_f, allow_unicode=True)
        return settings

    def create(self):
        with open('settings.yaml', 'r', encoding='utf-8') as f:
            result = f.read()
            settings = yaml.load(result, Loader=yaml.FullLoader)
        try:
            if settings['userInfo']['isFullInfo'] == 0:
                settings = self.generate_settings()
        except KeyError:
            settings = self.generate_settings()

        # self.headers['X-CSRF-Token'] = settings['userInfo']['csrf']
        self.cookie = settings['userInfo']['cookie']
        self.headers['X-CSRF-Token'] = self.get_csrf_token()

        del settings['userInfo']

        date = time.strftime('%Y-%m-%d')

        # 填报日期
        settings["values"]["_widget_1581259263910"] = {
            "data": int(time.mktime(time.strptime(date + ' 00:00:00', "%Y-%m-%d %H:%M:%S")))*1000,
            "visible": True
        }

        # 确认信息
        settings["values"]["_widget_1581259263913"]["data"] = date + \
            '-'+settings["values"]["_widget_1581259263913"]["data"]

        # 体温
        settings["values"]["_widget_1597486309838"] = {
            "data": [
                {
                    "_widget_1597486309854": {
                        "data": "36."+str(random.randint(0, 7))  # 早晨
                    },
                    "_widget_1597486309914": {
                        "data": "36."+str(random.randint(0, 7))  # 中午
                    },
                    "_widget_1597486309943": {
                        "data": "36."+str(random.randint(0, 7))  # 晚上
                    }
                }
            ],
            "visible": True
        }

        response = requests.post(self.urls[10], data=json.dumps(settings),
                                 headers=self.headers, cookies=self.cookie)
        return response
        # return settings


if __name__ == '__main__':
    urls = [
        'https://open.work.weixin.qq.com/wwopen/sso/3rd_qrConnect?appid=wx9b3c77819130e35c&redirect_uri=https%3A%2F%2Fwww.jiandaoyun.com%2Fwechat%2Fcorp%2Fauth%3Fredirect_uri%3D%252Fdashboard&usertype=member',
        'https://open.work.weixin.qq.com/wwopen/sso/qrImg?key=',
        'https://open.work.weixin.qq.com/wwopen/sso/l/qrConnect?callback=jsonpCallback&key={0}&redirect_uri=https%3A%2F%2Fwww.jiandaoyun.com%2Fwechat%2Fcorp%2Fauth%3Fredirect_uri%3D%252Fdashboard&appid=wx9b3c77819130e35c&_={1}',
        'https://www.jiandaoyun.com/wechat/corp/auth?redirect_uri=%2Fdashboard&auth_code={}&appid=wx9b3c77819130e35c',
        'https://www.jiandaoyun.com/dashboard',
        'https://www.jiandaoyun.com/corp/login_user_info',
        'https://www.jiandaoyun.com/dashboard/apps',
        'https://www.jiandaoyun.com/_/app/',
        'https://www.jiandaoyun.com/_/app/{0}/form/{1}',
        'https://www.jiandaoyun.com/_/data/link',
        'https://www.jiandaoyun.com/_/data/create'
    ]

    headers = {
        'Referer': 'https://open.work.weixin.qq.com/wwopen/sso/3rd_qrConnect?appid=wx9b3c77819130e35c&redirect_uri=https%3A%2F%2Fwww.jiandaoyun.com%2Fwechat%2Fcorp%2Fauth%3Fredirect_uri%3D%252Fdashboard&usertype=member',
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1',
        'Content-Type': 'application/json;charset=utf-8'
    }

    jdy = Jdy(urls, headers)
    response = jdy.create()

    # with open('created_settings.json', 'w', encoding='utf8') as f:
    #     json.dump(response, f, ensure_ascii=False)
    # with open('test.json', 'w') as f:
    #     json.dump(response.text, f, ensure_ascii=False)

    res = json.loads(response.text)

    try:
        check_code = res['check_code']
        if check_code == 0:
            print('打卡成功')
        else:
            raise Exception('错误的状态码')
    except KeyError as k:
        print("错误信息：返回值中没有check_code")
        print("返回值：", response.text)
        print('打卡失败')
    except Exception as e:
        print("错误信息：", e)
        print("返回值：", response.text)
        print('打卡失败')
    if os.path.exists('qrcode.jpg'):
        os.remove('qrcode.jpg')
