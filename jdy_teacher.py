#!/usr/bin/env python
# -*- coding:utf-8 -*-
# Copyright (c) 2021 pigeoner All rights reserved.
# 简道云自动打卡脚本（教师版）
# 第一次运行需要填写Jdy类的cookie属性，或者扫码自动获取cookie
# cookie和需要提交的表单信息在第一次运行后会自动保存到同目录的config.json文件下
# 定位的详细地址（location）需要手动填写，或者使用默认值

import requests
import time
import re
from PIL import Image
import json
import random
import yaml
import datetime
import os


class Jdy:
    def __init__(self, urls, headers):
        self.urls = urls
        self.headers = headers
        self.key = None
        self.auth_code = None
        self.cookie = None  # 这里可以填写自己的cookie
        self.csrf = None
        self.userInfo = None
        self.appId = None
        self.entryId = None
        self.entryDetails = None

    def get_key(self):

        self.headers['Referer'] = 'https://open.work.weixin.qq.com/wwopen/sso/3rd_qrConnect?appid=wx9b3c77819130e35c&redirect_uri=https%3A%2F%2Fwww.jiandaoyun.com%2Fwechat%2Fcorp%2Fauth%3Fredirect_uri%3D%252Fdashboard&usertype=member'
        html = requests.get(self.urls[0], headers=self.headers)
        key = re.search("(?<=\"key\"\:\")(.*?)(?=\")",
                        html.content.decode()).group(1)
        self.key = key
        del self.headers['Referer']
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
        self.userInfo = json.loads(html.text)
        return html.content

    def get_appId(self):

        html = requests.post(
            self.urls[6], headers=self.headers, cookies=self.cookie)
        res = json.loads(html.content.decode())['apps']
        for e in res:
            if e['name'] == '教师工作部':
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
            if res['entryMap'][e]['name'] == '每日信息填报':
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

        if self.cookie is None or len(self.cookie) == 0 or not hasattr(self, 'cookie'):
            self.get_key()
            self.show_qrcode()
            self.get_auth_code()
            self.get_cookie()
        self.get_csrf_token()
        self.get_user_info()
        self.get_appId()
        self.get_entryId()
        self.get_entry_details()

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

        nameId = self.userInfo["memberInfo"]["member_id"]
        tchNo = self.userInfo["memberInfo"]["username"]
        name = self.userInfo["memberInfo"]["nickname"]

        department = get_widget_value('_widget_1581259263911', tchNo)
        tel = get_widget_value('_widget_1582001600375', tchNo)
        tchOrWorker = get_widget_value('_widget_1581863555361', tchNo)
        isBeijinger = get_widget_value('_widget_1581484253473', tchNo)

        confirm = department + '-' + tchNo + '-' + name

        location = {
            'province': '北京市',  # 省份
            'city': '北京市',  # 城市
            'district': '朝阳区',  # 区
            'detail': '中国传媒大学'  # 详细地址
        }

        addressUrl = 'https://www.jiandaoyun.com/_/data/formula/aggregate'
        addrPayload = {
            "op": "last",
            "appId": self.appId,
            "entryId": self.entryId,
            "formId": self.entryId,
            "lookup_value": tchNo,
            "lookup_field": "_widget_1581325409790",
            "result_field": "_widget_1596350939077",
            "date_type": False
        }
        res = requests.post(addressUrl, data=json.dumps(addrPayload),
                            headers=self.headers, cookies=self.cookie)
        address = json.loads(res.text)['result'][0]['result']

        zhishu = get_widget_value(
            '_widget_1595295790983', department)[0]['_id']
        yuanbu = get_widget_value(
            '_widget_1595640862974', department)[0]['_id']
        yiqing = get_widget_value(
            '_widget_1610602225472', department)[0]['_id']
        dangwei = get_widget_value(
            '_widget_1610602225490', department)[0]['_id']
        yuanzhang = get_widget_value(
            '_widget_1610602225508', department)[0]['_id']

        settings = {
            "userInfo": {
                "cookie": self.cookie
            },
            "values": {
                "_widget_1610371684526": {  # 当前用户
                    "data": nameId,
                    "visible": False
                },
                "_widget_1581259263912": {  # 姓名
                    "data": nameId,
                    "visible": True
                },
                "_widget_1610371685527": {  # 是否为代填
                    "data": "否",
                    "visible": False
                },
                "_widget_1581325409790": {  # 工作证号
                    "data": tchNo,
                    "visible": True
                },
                "_widget_1581259263911": {  # 直属部门
                    "data": department,
                    "visible": False
                },
                "_widget_1582001600375": {  # 手机号码
                    "data": tel,
                    "visible": False
                },
                "_widget_1581863555361": {  # 教师/员工
                    "data": tchOrWorker,
                    "visible": False
                },
                "_widget_1581484253473": {  # 京籍/非京籍
                    "data": isBeijinger,
                    "visible": False
                },
                "_widget_1581259263913": {  # 填报确认
                    "data": confirm,
                    "visible": True
                },
                "_widget_1594972479663": {  # 目前所在地
                    "data": "北京",
                    "visible": True
                },
                "_widget_1616249984936": {  # 3当前所在城市
                    "data": "北京市",
                    "visible": False
                },
                "_widget_1616249985008": {  # 上次填报确认
                    "data": confirm,
                    "visible": False
                },
                "_widget_1616249984917": {  # 2上次所在地
                    "data": "北京",
                    "visible": False
                },
                "_widget_1616249984955": {  # 4上次所在城市
                    "data": "北京市",
                    "visible": False
                },
                "_widget_1594972480348": {  # 定位所在地/街道
                    "data": location,
                    "visible": True
                },
                "_widget_1613721964143": {  # 当前位置
                    "data": location['district'],
                    "visible": False
                },
                "_widget_1594972480502": {  # 所在地/街道
                    "visible": False
                },
                "_widget_1616457553831": {  # 所在地变动信息
                    "data": "无变化",
                    "visible": True
                },
                "_widget_1595580335402": {  # 目前所在地较昨日是否有变化
                    "visible": False
                },
                "_widget_1595602792466": {  # 请填写变动信息
                    "visible": False
                },
                "_widget_1581780613796": {  # 返京信息
                    "data": [],
                    "visible": False
                },
                "_widget_1594947270924": {  # 离京或京外地点变动信息
                    "data": [],
                    "visible": False
                },
                "_widget_1594947271819": {  # 回国或出境信息
                    "data": [],
                    "visible": False
                },
                "_widget_1596350939077": {  # 在京常住地址
                    "data": address,
                    "visible": True
                },
                "_widget_1594972480810": {  # 目前所在地是否为中高风险地区
                    "data": "否",
                    "visible": True
                },
                "_widget_1594972480931": {  # 中高风险地区/街道
                    "visible": False
                },
                "_widget_1616409660827": {  # 体温情况
                    "data": "正常",
                    "visible": False
                },
                "_widget_1616409886830": {  # 是否有咳嗽、腹泻、乏力等症状？
                    "data": "否",
                    "visible": True
                },
                "_widget_1594974441797": {  # 目前身体健康状况
                    "data": "健康",
                    "visible": False
                },
                "_widget_1594974441946": {  # 是否为疑似或确诊
                    "data": "否",
                    "visible": False
                },
                "_widget_1598446955582": {  # 假期期间本人或共同居住家庭成员是否在中高风险地区居住或有无中高风险地区、境外旅行史？
                    "data": "否",
                    "visible": False
                },
                "_widget_1598616012193": {  # 1.请说明详细情况
                    "visible": False
                },
                "_widget_1598446955614": {  # 本人或共同居住家庭成员是否为或曾为确诊、疑似病例，核酸检测阳性者、无症状病例、密切接触者？
                    "data": "否",
                    "visible": False
                },
                "_widget_1598616012398": {  # 2.请说明详细情况
                    "visible": False
                },
                "_widget_1598446955631": {  # 共同居住家庭成员有无发热、咳嗽、腹泻等症状且排除新冠病毒感染
                    "data": "否",
                    "visible": False
                },
                "_widget_1598616012431": {  # 3.请说明详细情况
                    "visible": False
                },
                "_widget_1581484254358": {  # 申请入校
                    "data": [],
                    "visible": False
                },
                "_widget_1595295790983": {  # 直属部门审核人
                    "data": [
                        zhishu
                    ],
                    "visible": True
                },
                "_widget_1595640862974": {  # 院部机关审核人
                    "data": [
                        yuanbu
                    ],
                    "visible": True
                },
                "_widget_1610602225472": {  # 疫情防控工作负责人
                    "data": [
                        yiqing
                    ],
                    "visible": False
                },
                "_widget_1610602225490": {  # 党委/党总支/直属党支部书记
                    "data": [
                        dangwei
                    ],
                    "visible": False
                },
                "_widget_1610602225508": {  # 院长/副书记
                    "data": [
                        yuanzhang
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

        with open('config.json', 'w', encoding='utf8') as f:
            json.dump(settings, f, ensure_ascii=False)
        return settings

    def create(self):
        if os.path.exists('config.json'):
            with open('config.json', 'r', encoding='utf-8') as f:
                settings = json.load(f)
                self.cookie = settings['userInfo']['cookie']
                self.get_csrf_token()
        else:
            settings = self.generate_settings()

        del settings['userInfo']

        date = time.strftime('%Y-%m-%d')

        # 填报日期
        settings["values"]["_widget_1581259263910"] = {
            "data": int(time.mktime(time.strptime(date + ' 00:00:00', "%Y-%m-%d %H:%M:%S")))*1000,
            "visible": False
        }

        # 确认信息
        settings["values"]["_widget_1581259263913"]["data"] = date + \
            '-'+settings["values"]["_widget_1581259263913"]["data"]

        # 上次确认信息
        settings["values"]["_widget_1616249985008"]["data"] = str(datetime.date.today(
        ) + datetime.timedelta(-1)) + '-' + settings["values"]["_widget_1616249985008"]["data"]

        location = settings["values"]["_widget_1594972480348"]
        gaodeUrl = 'https://restapi.amap.com/v3/geocode/geo?key=6f9c62f150c3ed0f69d276eac714e584&address='
        gaodeRes = requests.get(gaodeUrl+location['data']['detail'])
        geo = json.loads(gaodeRes.text)[
            'geocodes'][0]['location'].split(',')
        geo = [float(num) for num in geo]
        location['data']['lnglatXY'] = geo

        # 体温
        temperature = [
            float(int(random.uniform(36, 37)*10))/10 for i in range(3)]
        settings["values"]["_widget_1616409319134"] = {  # 体温
            "data": [
                {
                    "_widget_1616409586030": {  # 最高体温
                        "data": max(temperature)
                    },
                    "_widget_1616474253399": {  # 晨
                        "data": temperature[0]
                    },
                    "_widget_1616474253473": {  # 午
                        "data": temperature[1]
                    },
                    "_widget_1616474253547": {  # 晚
                        "data": temperature[2]
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
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1',
        'Content-Type': 'application/json;charset=utf-8'
    }

    jdy = Jdy(urls, headers)

    # with open('test.json', 'w', encoding='utf8') as f:
    #     json.dump(jdy.create(), f, ensure_ascii=False)
    # print(jdy.create())

    response = jdy.create()
    # with open('response.json', 'w') as f:
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
