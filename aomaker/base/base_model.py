import random
from typing import Any
from faker import Faker
from regex_string_generator import generate_string
from typing import Type

from aomaker.exceptions import ParamsException


class Params:
    def __new__(cls, mapping: str = None, default: Any = None, regex: str = None) -> tuple:
        """
        参数设置
        :param mapping:映射key，映射到实际传入用例到参数，默认为字段自身
        :param default: 默认值，设定后每次请求都会为此字段赋此默认值，为{}时表示根据字段type随机mock
        :param regex: 正则表达式，传入后每次实例化会根据正则生成随机数据
        """
        return mapping, default, regex


class Model(dict):

    @staticmethod
    def fake(type: Type):
        faker = Faker()
        res = None
        match type.__name__:
            case 'str':
                res = faker.pystr(max_chars=10, min_chars=10)
            case 'int':
                res = faker.random_int(max=100000000)
            case 'bool':
                res = random.choice([True, False])
        return res

    def __new__(cls, **kwargs: Any) -> Any:
        """
        请求参数Model基类，参数过多时使用Model管理维护
        返回在子类中定义的所有字段及其默认值，若定义为None且未传入，返回时滤掉该字段
        :param kwargs: 传入的字段值
        :return 最终的请求参数
        """
        res = dict()
        mapping_keys = []
        annotations = cls.__annotations__  # 获取类的所有字段和注解
        for name, data_type in annotations.items():  # 遍历所有字段和注解
            mapping, default, regex = getattr(cls, name)
            if mapping is None:
                mapping = name
            mapping_keys.append(mapping)
            if mapping not in kwargs:  # 检查 kwargs 中是否存在该字段
                # if data_type.__name__ not in ['str', 'int', 'bool']:
                #     raise ParamsException(f'非常态参数为必传参数: {name}')
                if default == '{}':
                    res[name] = cls.fake(data_type)
                elif regex:
                    res[name] = type(generate_string(regex))
                elif default and default != '{}':
                    if not isinstance(default, data_type):
                        raise ParamsException(f'参数设定的默认值不符定义: {name}')
                    res[name] = default
                else:
                    res[name] = None
            else:
                if not isinstance(kwargs[mapping], data_type):
                    raise ParamsException(f'参数类型传入错误: {name}')
                res[name] = kwargs[mapping]
        kwargs_keys = kwargs.keys()
        if not set(kwargs_keys).issubset(set(mapping_keys)):
            diff = set(kwargs_keys).difference(set(mapping_keys))
            raise ParamsException(f'传入未知映射Key: {diff}')
        return {k: v for k, v in res.items() if v is not None}  # 返回结果并滤掉为None且未传入的字段
