# -*- coding: utf-8 -*-
"""
@File                : yiban.py
@Github              : https://github.com/Jayve
@Last modified by    : Jayve
@Last modified time  : 2021-7-1 10:52:15
"""
import logging
import random
import re
import time
import uuid
from urllib.parse import urlparse, unquote

import requests
import urllib3
from requests import HTTPError
from urllib3.exceptions import InsecureRequestWarning

import utils

log = logger = logging
random.seed()


def version():
    return 'v2.0.2'


class YiBan:
    USERAGENTS = [
        "Mozilla/5.0 (Linux; Android 10; VOG-AL00 Build/HUAWEIVOG-AL00) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/88.0.4324.181 Mobile Safari/537.36 yiban_android",
        "Mozilla/5.0 (Linux; Android 9; Redmi Note 7 Build/PKQ1.180904.001) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/80.0.3578.141 Mobile Safari/537.36 yiban_android",
        "Mozilla/5.0 (Linux; Android 9; HLK-AL10 Build/HONORHLK-AL10) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/81.0.3809.89 Mobile Safari/537.36 yiban_android",
        "Mozilla/5.0 (Linux; Android 10; SEA-AL10 Build/HUAWEISEA-AL10) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/80.0.3809.89 Mobile Safari/537.36 yiban_android",
        "Mozilla/5.0 (Linux; Android 10; MI 9 Build/QKQ1.190825.002) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/80.0.3396.87 Mobile Safari/537.36 yiban_android",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 11_4_1 like Mac OS X) AppleWebKit/601.3.9 (KHTML, like Gecko) Version/10.0 Mobile/15E148 yiban_android",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 11_2_6 like Mac OS X) AppleWebKit/604.3.5 (KHTML, like Gecko) Version/11.0 MQQBrowser/10.1.0 Mobile/15B87 Safari/604.1 yiban_android"
    ]

    def __init__(self, account, passwd, ua: int = None, debug=False):
        self.HEADERS = {
            # "Accept": "application/json, text/plain, */*",
            # "Origin": "https://xsgl.jlau.edu.cn",
            "User-Agent": ua if ua else self.USERAGENTS[random.randint(0, len(self.USERAGENTS) - 1)],
            # "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            # "Referer": "https://xsgl.jlau.edu.cn/webApp/xuegong/index.html",
            "Accept-Encoding": "gzip, deflate",
            # "Accept-Language": "zh-CN,en-US;q=0.8",
            "appversion": "4.9.10",
            # "signature": "",
            # "logintoken": self.access_token,
            # "authorization": f"Bearer {self.access_token}",
            "X-Requested-With": "com.yiban.app"
        }
        self.account = account
        self.passwd = passwd
        self.access_token = ''
        self.session = requests.session()
        self.name = ''
        self.iapp = ''
        self.debug = debug
        if self.debug:
            urllib3.disable_warnings(InsecureRequestWarning)

    def request(self, url, method="get", data=None, params=None, json=None, headers=None, cookies=None,
                max_retry: int = 2, **kwargs):
        headers = self.HEADERS if not headers else headers
        for i in range(max_retry + 1):
            try:
                response = self.session.request(method, url, params=params, data=data, json=json, headers=headers,
                                                cookies=cookies, verify=not self.debug, **kwargs)
            except HTTPError as e:
                log.error(f'HTTP错误:\n{e}')
                log.error(f'第 {i + 1} 次请求失败, 重试...')
            except KeyError as e:
                log.error(f'错误返回值:\n{e}')
                log.error(f'第 {i + 1} 次请求失败, 重试...')
            except Exception as e:
                log.error(f'未知异常:\n{e}')
                log.error(f'第 {i + 1} 次请求失败, 重试...')
            else:
                return response
        raise Exception(f'已重试 {max_retry + 1} 次，HTTP请求全部失败, 放弃.')

    def login(self):
        data = {
            "mobile": self.account,
            "imei": 0,
            "password": self.passwd
        }
        # 调用v3接口登录，无需加密密码
        res = self.request(url="https://mobile.yiban.cn/api/v3/passport/login", method='post', data=data)
        try:
            r = utils.resp_parse_json(resp=res)
        except Exception as e:
            raise Exception(f"登录易班发生错误 {str(e)}")

        # {'response': 100, 'message': '请求成功', 'data': {****}}
        # {'response': 101, 'message': '服务忙，请稍后再试。', 'data': []}
        if r:
            if 'response' in r and r["response"] == 100:
                self.access_token = r["data"]["user"]["access_token"]
                self.name = r["data"]["user"]["nick"]
                self.HEADERS.update({
                    "logintoken": self.access_token,
                    "authorization": f"Bearer {self.access_token}"
                })
                return r
            else:
                message = r['message']
                raise Exception(f'登录易班发生错误：{message}')
        else:
            raise Exception('易班登录返回结果异常，为空')

    def get_home_jlau(self):
        params = {
            "access_token": self.access_token,
        }
        res = self.request(url="https://mobile.yiban.cn/api/v3/home", params=params)
        try:
            r = utils.resp_parse_json(resp=res)
        except Exception as e:
            raise Exception(f"请求iapp列表发生错误 {repr(e)} {res.text[:101]}")

        # {'response': 100, 'message': '请求成功', 'data': {****}}
        # {'response': 101, 'message': '服务忙，请稍后再试。', 'data': []}
        if r:
            if 'response' in r and r["response"] == 100:
                # 获取iapp号
                for app in r["data"]["hotApps"]:
                    if app["name"] == "吉农学工系统":
                        self.iapp = re.findall(r"(iapp.*)\?", app["url"])[0].split("/")[0]
                return r
            else:
                message = r['message']
                raise Exception(f'请求iapp列表发生错误 {message}')
        else:
            raise Exception('易班返回iapp列表异常，为空')

    def do_auth_home(self):
        if self.iapp == "":
            self.get_home_jlau()
        v_time = utils.get_v_time()

        # 获取waf_cookie
        ex_headers = {

        }
        params = {
            "act": self.iapp
            # "v": self.access_token
        }
        url = f"http://f.yiban.cn/{self.iapp}/i/{self.access_token}?v_time={v_time}"
        self.request(url, allow_redirects=False)  # 此次请求的响应会往cookie池追加waf_cookie=xxxx

        # 向易班获取iapp入口
        r = self.request(url="http://f.yiban.cn/iapp/index", headers={**self.HEADERS, **ex_headers}, params=params,
                         allow_redirects=False)
        location = r.headers.get("Location")

        # location = https://xsgl.jlau.edu.cn/nonlogin/yiban/authentication/4a46818571558ef9017155f721f20012.htm
        # ?verify_request=&yb_uid=
        if not location:
            if 'html' in r.text:
                message = re.findall("(?<=<title>).*(?=</title>)", r.text)[0]
                raise Exception(f'获取iapp入口遇到错误 {message}')
            else:
                # 该用户可能没进行校方认证，无此APP权限
                message = r.text[:101]
                raise Exception(f'获取iapp入口遇到错误 {message}')

        # 登录学工系统
        # 有几率登不上，wdnmd干爆
        authQYY_location = None
        retry_cont = 2
        for i in range(retry_cont + 1):
            url = location
            r = self.request(url, allow_redirects=False)
            authQYY_location = r.headers.get("Location")
            if authQYY_location:
                break
            elif i >= retry_cont:  # 达到最大尝试次数
                if "<html>" in r.text:
                    message = re.findall("(?<=<title>).*(?=</title>)", r.text)[0]
                    raise Exception(f"登录学工系统时遇到服务器错误 {message}")
                else:
                    message = r.text[:201]
                    raise Exception(f"登录学工系统时遇到服务器错误 {message}")
            time.sleep(5.0)

        # authQYY_location有两种情况 取决于iapp是否已授权
        # 已授权返回Location https://xsgl.jlau.edu.cn/yiban/authorize.html
        # 未授权返回Location https://openapi.yiban.cn/oauth/authorize

        # 首次进入iapp，需要点击授权
        if "oauth/authorize" in authQYY_location:
            data = {'scope': '1,2,3,4,'}
            query_params = urlparse(authQYY_location).query.split('&')
            # log.debug(query_params)
            for line in query_params:
                title, value = str(line).split("=")
                data[title] = value
            data['redirect_uri'] = unquote(data['redirect_uri'], 'utf-8')
            data['display'] = 'html'
            # 模拟确认授权
            resp = self.request('https://oauth.yiban.cn/code/usersure', method='post', data=data)
            try:
                r = utils.resp_parse_json(resp=resp)
            except Exception as e:
                raise Exception(f"授权iapp时遇到错误 {str(e)}")
            # 检查是否授权成功
            # {"code":"s200","reUrl":"https:\/\/f.yiban.cn\/iapp619789\/v\/0e4200ff23de1faa22a2cd6e07615767"}
            if r['code'] != 's200':
                if 'msgCN' in r:
                    fail_reason = r['msgCN']
                    raise Exception(f'授权iapp时遇到错误 {fail_reason}')
                else:
                    raise Exception(f'授权iapp时遇到错误 {r.status_code}')
            # 授权成功，模拟客户端行为，访问跳转地址
            self.request(r['reUrl'])

        # 正式登录学工系统
        compressedCode = authQYY_location.split('?')[1].split('=')[1]
        if not compressedCode:
            raise Exception('登录学工系统遇到异常,compressedCode为空')
        params = {
            'compressedCode': compressedCode,
            'deviceId': uuid.uuid1()
        }
        res = self.request(url='https://xsgl.jlau.edu.cn/nonlogin/yiban/authQYY.htm', params=params,
                           allow_redirects=False)
        if res.headers.get('Location') == 'https://xsgl.jlau.edu.cn/webApp/xuegong/index.html#/action/baseIndex/':
            return True
        else:
            return False

    def get_sign_tasks(self):
        data = {
            'pageIndex': 0,
            'pageSize': 10,
            'type': 'yqsjcj'
        }
        res = self.request("https://xsgl.jlau.edu.cn/syt/zzapply/queryxmqks.htm", method='post', data=data)
        try:
            r = utils.resp_parse_json(resp=res)
        except Exception as e:
            raise Exception(f"请求任务列表发生错误 {str(e)}")
        return r

    def get_sign_task_state(self, xmid):
        data = {
            "xmid": xmid,
            "pdnf": 2020
        }
        res = self.request("https://xsgl.jlau.edu.cn/syt/zzapply/checkrestrict.htm", method='post', data=data)
        if res.text == '':
            if res.status_code == 200:
                return '未签到'
            else:
                raise Exception(f"请求任务状态发生错误 {res.status_code}")
        elif 'html' in res.text:
            message = re.findall("(?<=<title>).*(?=</title>)", res.text)[0]
            raise Exception(f"请求任务状态发生错误 {message}")
        return res.text

    def get_sign_task_detail(self, xmid):
        data = {
            'projectId': xmid
        }
        res = self.request("https://xsgl.jlau.edu.cn/syt/zzapi/getBaseApplyInfo.htm", method='post', data=data)
        try:
            r = utils.resp_parse_json(resp=res)
        except Exception as e:
            raise Exception(f"请求任务详情发生错误 {str(e)}")
        return r

    def do_sign_submit(self, xmid, data):
        """
        :param xmid: 任务id
        :param data: 表单JSON
        :return: request
        例 提交表单
        data:
        {
          "xmqkb": { "id": "4a4681857601d718017603676e431b5c" },
          "c2": "健康",
          "c1": "35.7",
          "type": "yqsjcj",
          "location_longitude": 125.4096441219101,
          "location_latitude": 43.80706615137553,
          "location_address": "吉林省 长春市 南关区 新城大街 2888号 靠近吉林农业大学 "
        }
        """
        data = {
            "data": data,
            "msgUrl": f"syt/zzapply/list.htm?type=yqsjcj&xmid={xmid}",
            "multiSelectData": {},
            "uploadFileStr": {},
            "type": "yqsjcj"
        }
        res = self.request("https://xsgl.jlau.edu.cn/syt/zzapply/operation.htm", method='post', data=data)
        if 'html' in res.text:
            message = re.findall("(?<=<title>).*(?=</title>)", res.text)[0]
            raise Exception(message)
        elif res.status_code == 200:
            # 正常返回'success' 或 'Applied today'
            return res.text
        else:
            raise Exception(res.status_code)

    def get_signed_list(self, xmid, index=0, size=10):
        """
        :param xmid: 任务id
        :param index: 拉取页码索引
        :param size: 拉取任务数
        :return: request
        服务器返回值简例：{"data":[{"id":"4a46818578d4ec3601793f90c5f36fb4",...},{..},...]}
        """
        data = {
            "pageIndex": index,
            "pageSize": size,
            "xmid": xmid,
            "type": "yqsjcj"
        }
        resp = self.request("https://xsgl.jlau.edu.cn/syt/zzapply/queryxssqlist.htm", method='post', data=data)
        try:
            r = utils.resp_parse_json(resp=resp)
        except Exception as e:
            raise Exception(f'获取已签任务列表时遇到错误 {str(e)}')
        else:
            return r

    def do_sign_modify(self, xmid, data):
        """
        :param xmid: 任务id
        :param data: 表单JSON
        :return: request
        !!表单JSON中必须包含要修改的表单id(键名为"id")
        例 修改表单
        data:
        {
          "xmqkb": { "id": "4a4681857601d7180176036ceba11b6e" },
          "c1": "35.7",
          "c2": "健康",
          "type": "yqsjcj",
          "id": "4a46818578d4ec3601793f90c5f36fb4"
        }
        """
        if 'id' not in data:
            raise Exception('提交修改请求时，表单data必须包含要修改的表单id(键名为"id")')
        data = {
            "data": data,
            "msgUrl": f"syt/zzapply/list.htm?type=yqsjcj&xmid={xmid}",
            "multiSelectData": {},
            "uploadFileStr": {},
            "type": "yqsjcj"
        }
        return self.request("https://xsgl.jlau.edu.cn/syt/zzapply/operation.htm", method='post', data=data)

    def do_sign_remove(self, form_id):
        """
        :param form_id: 表单id
        :return: request
        删除签到记录
        响应：
        Content-Type：text/plain
        例：“success”
        """
        data = {
            "id": form_id,
            "type": "yqsjcj"
        }
        return self.request("https://xsgl.jlau.edu.cn/syt/zzapply/remove.htm", method='post', data=data)
