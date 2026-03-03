# -*- coding: utf-8 -*-
"""
一个用于与商超 ERP 系统交互的客户端，已适配 `async main` 函数规范。

核心功能：
- `main` 函数只接收 `username` 和 `password` 作为输入参数。
- 总是返回一个结构一致的字典，包含输入参数、执行结果和错误信息。
- 成功时，结果会填充在 `result` 字段中。
- 失败时，错误信息会填充在 `error` 字段中。
"""

import requests
import json

# --- 固定配置 ---
BASE_URL = "xxx"
LOGIN_PATH = "/erp/login"
PRODUCT_LIST_PATH = "/erp/shop/product/list"


class ERPClient:
    """
    ERP 接口客户端。
    负责处理登录、token 管理和 API 请求。
    """

    def __init__(self, base_url, username, password, timeout=10):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.timeout = timeout
        self.token = None

        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0"})

    def login(self):
        """执行登录并获取 token。"""
        print("正在尝试登录...")
        url = self.base_url + LOGIN_PATH
        payload = {"username": self.username, "password": self.password}

        try:
            resp = self.session.post(url, json=payload, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            new_token = data.get("token")
            if not new_token:
                raise KeyError("登录响应中未找到 'token' 字段。")
            self.token = new_token
            print("登录成功，已获取新的 token。")
        except requests.RequestException as e:
            raise RuntimeError(f"登录请求失败: {e}")
        except (KeyError, ValueError) as e:
            raise RuntimeError(f"解析登录响应失败: {e}")

    def get(self, path, params=None):
        """发送 GET 请求，并处理 token 失效重试。"""
        if not self.token:
            self.login()

        url = self.base_url + path
        headers = {"Authorization": f"Bearer {self.token}"}
        resp = self.session.get(url, headers=headers, params=params, timeout=self.timeout)

        if resp.status_code == 401:
            print("Token 已失效，正在重新登录并重试...")
            self.login()
            headers = {"Authorization": f"Bearer {self.token}"}
            resp = self.session.get(url, headers=headers, params=params, timeout=self.timeout)

        return resp

    def fetch_product_list(self, params):
        """获取商品列表。"""
        print("\n正在查询商品列表...")
        response = self.get(PRODUCT_LIST_PATH, params=params)
        response.raise_for_status()
        return response.json()


async def main(args):
    """
    主执行函数。

    :param args: 一个包含 `params` 字典的对象。
                 `params` 必须包含 `username` 和 `password`。
    :return: 一个结构固定的字典，包含输入、结果和错误信息。
    """
    params = args.params
    username = params.get("username")
    password = params.get("password")

    # 初始化一个结构固定的返回字典，以确保返回格式的一致性
    output = {
        "inputs": {"username": username},
        "result": None,
        "error": None
    }

    if not username or not password:
        output["error"] = "输入参数错误，必须提供 'username' 和 'password'。"
        return output

    # 商品查询参数（固定值）
    product_query_params = {
        "pageNum": 1,
        "pageSize": 10,
        "type": 1,
        "isDel": 0
    }

    try:
        # 1. 创建客户端
        client = ERPClient(BASE_URL, username, password)

        # 2. 获取数据
        product_data = client.fetch_product_list(params=product_query_params)

        # 3. 成功时，将商品列表放入 'result' 字段
        output["result"] = product_data

    except (RuntimeError, requests.RequestException) as e:
        # 4. 失败时，将错误信息放入 'error' 字段
        error_message = f"程序执行出错: {e}"
        print(f"\n{error_message}")
        output["error"] = error_message
    
    # 5. 返回结构一致的 output 字典
    return output
