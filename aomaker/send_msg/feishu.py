# --coding:utf-8--
import requests
import os

from aomaker.utils.gen_allure_report import CaseSummary, get_allure_results
from aomaker.utils.utils import load_yaml
from aomaker.cache import Config
from aomaker.path import CONF_DIR
from aomaker._constants import Conf

utils_yaml_path = os.path.join(CONF_DIR, Conf.UTILS_CONF_NAME)


class FeiShu:
    """
    企业微信消息通知
    """

    def __init__(self, tester="fj", title="自动化测试通知", report_address=""):
        self.feishu_conf = load_yaml(utils_yaml_path)['feishu']
        self.curl = 'https://open.feishu.cn/open-apis/bot/v2/hook/cb40e843-c4c1-4d08-a1ba-003eedb79fcc'
        self.headers = {"Content-Type": "application/json"}
        self.test_results = CaseSummary()
        self.total = str(self.test_results.total_count)
        self.passed = str(self.test_results.passed_count)
        self.failed = str(self.test_results.failed_count)
        self.skipped = str(self.test_results.skipped_count)
        self.broken = str(self.test_results.broken_count)
        self.passed_rate = self.test_results.passed_rate
        self.duration = self.test_results.duration
        self.config_db = Config()
        self.current_env = self.config_db.get('current_env')
        self.tester = tester
        self.title = title
        self.report_address = report_address

    def _send_markdown(self, content):
        json_data = {
            "config": {
                "update_multi": True
            },
            "i18n_elements": {
                "zh_cn": [
                    {
                        "tag": "markdown",
                        "content": content,
                        "text_align": "left",
                        "text_size": "normal"
                    }
                ]
            },
            "i18n_header": {
                "zh_cn": {
                    "title": {
                        "tag": "plain_text",
                        "content": "自动化测试通知"
                    },
                    "subtitle": {
                        "tag": "plain_text",
                        "content": ""
                    },
                    "text_tag_list": [
                        {
                            "tag": "text_tag",
                            "text": {
                                "tag": "plain_text",
                                "content": "Interface"
                            },
                            "color": "neutral"
                        }
                    ],
                    "template": "blue",
                    "ud_icon": {
                        "tag": "standard_icon",
                        "token": "vote_colorful"
                    }
                }
            }
        }
        res = requests.post(url=self.curl, json=json_data, headers=self.headers)
        if res.json()['errcode'] != 0:
            raise ValueError(f"企业微信「MarkDown类型」消息发送失败")

    def send_detail_msg(self, sep="_"):
        reports = get_allure_results(sep=sep)
        if reports:
            markdown_li = []
            for product, result in reports.items():
                format_ = f"><font color=\"info\">🎯「{product}」成功率: {result['passed_rate']}</font>"
                markdown_li.append(format_)
            format_product_rate = "\n".join(markdown_li)
        else:
            format_product_rate = ""
        text = (f"**基本信息**\n"
                f" - ❤用例  总数：<font color=\\\"info\\\">{self.total}个</font>\n\n\n"
                f"**执行结果**\n- <font color=\\\"info\\\">"
                f"- 🎯运行成功率: {self.passed_rate}</font>\n{format_product_rate}\n"
                f"- 😁成功用例数：<font color=\\\"info\\\">{self.passed}个</font>\n"
                f"- 😭失败用例数：`{self.failed}个`\n"
                f"- 😡阻塞用例数：`{self.broken}个`\n"
                f"- 😶跳过用例数：<font color=\\\"warning\\\">{self.skipped}个</font>\n"
                f"- 🕓用例执行时长：<font color=\\\"warning\\\">{self.duration}</font>\n\n\n"
                f"**测试报告**\n"
                f"- 📉[查看>>测试报告]({self.report_address})")
        self._send_markdown(text)
        self.config_db.close()
