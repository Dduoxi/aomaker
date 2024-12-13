# --coding:utf-8--
import os
import importlib
from types import NoneType
from typing import List, Dict, Callable, Text, Tuple, Union, Optional
from functools import wraps
from dataclasses import dataclass as dc, field

import yaml
import click
from jsonpath import jsonpath
from genson import SchemaBuilder

from aomaker.cache import cache
from aomaker.log import logger
from aomaker.path import BASEDIR
from aomaker.exceptions import FileNotFound, YamlKeyError, JsonPathExtractFailed, CompareException
from aomaker.hook_manager import cli_hook, session_hook
from aomaker.models import ExecuteAsyncJobCondition


# def dependence(dependent_api: Callable or str, var_name: Text, imp_module=None, *out_args, **out_kwargs):
#     """
#     接口依赖调用装饰器，
#     会在目标接口调用前，先去调用其前置依赖接口，然后存储依赖接口的完整响应结果到cache表中，key为var_name
#     若var_name已存在，将不会再调用该依赖接口
#
#     :param dependent_api: 接口依赖，直接传入接口对象；若依赖接口是同一个类下的方法，需要传入字符串：类名.方法名
#     :param var_name: 依赖的参数名
#     :param imp_module: 若依赖接口是同一个类下的方法，需要导入模块
#     :param out_args: 依赖接口需要的参数
#     :param out_kwargs: 依赖接口需要的参数
#     :return:
#     """
#
#     def decorator(func):
#         @wraps(func)
#         def wrapper(*args, **kwargs):
#             api_name = func.__name__
#             if not cache.get(var_name):
#                 dependence_res, depend_api_info = _call_dependence(dependent_api, api_name, imp_module=imp_module,
#                                                                    *out_args, **out_kwargs)
#                 depend_api_name = depend_api_info.get("name")
#                 cache.set(var_name, dependence_res, api_info=depend_api_info)
#
#                 logger.info(f"==========存储全局变量{var_name}完成==========")
#                 logger.info(f"==========<{api_name}>前置依赖<{depend_api_name}>结束==========")
#             else:
#                 logger.info(
#                     f"==========<{api_name}>前置依赖已被调用过，本次不再调用,依赖参数{var_name}直接从cache表中读取==========")
#             r = func(*args, **kwargs)
#             return r
#
#         return wrapper
#
#     return decorator

def get_value_by_jsonpath(jsonpath_expr, datasource):
    if ':' in jsonpath_expr:
        json_path, index = jsonpath_expr.split(':')
    else:
        index = 0
    extract_var = jsonpath(datasource, jsonpath_expr)
    if extract_var is False:
        raise JsonPathExtractFailed(datasource, jsonpath_expr)
    return extract_var[index]


def dependence(dependent_api: Callable or str, var_name: Text, require: bool = False, refresh: bool = False, *out_args):
    """
    接口依赖调用装饰器，
    会在目标接口调用前，先去调用其前置依赖接口，然后存储依赖接口的完整响应结果到cache表中，key为var_name
    若var_name已存在，将不会再调用该依赖接口
    :param dependent_api: 接口依赖，直接传入接口对象；若依赖接口是同一个类下的方法，需要传入字符串：类下实例化的对象.方法名
    :param var_name: 依赖的参数名
    :param require: 请求是否需要参数传入
    :param refresh: 此依赖是否每次请求都需要刷新，默认为否
    :return:
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            api_name = func.__name__
            imp_module = func.__module__
            try:
                dependent_param = kwargs['dependence'][var_name] if require else dict()
            except KeyError:
                logger.info(f"==========<{api_name}>前置依赖{var_name}方法未传入依赖参数跳过执行==========")
                r = func(*args, **kwargs)
                return r
            if not cache.get(var_name) or refresh:
                dependence_res, depend_api_info = _call_dependence(dependent_api, api_name, imp_module,
                                                                   *out_args, **dependent_param)
                depend_api_name = depend_api_info.get("name")
                logger.info(f"==========<{api_name}>前置依赖<{depend_api_name}>结束==========")
            else:
                logger.info(
                    f"==========<{api_name}>前置依赖已被调用过，本次不再调用,依赖参数{var_name}直接从cache表中读取==========")

            r = func(*args, **kwargs)
            return r

        return wrapper

    return decorator


def be_dependence(var_name: Text, condition: Union[Dict, bool], jsonpath_expr: str = ""):
    """
    标明此接口被其他接口所依赖，会将其响应结果存储，key为var_name
    :param var_name:存储响应结果使用的key
    :param jsonpath_expr: jsonpath用于查找响应结果的某字段,未传入则存储整段响应
    :param condition: 通过`:`分割后用jsonpath查找到的结果判断是否此条件，为True时才会存入cache表，未传入默认均存入
    :return:
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            resp = func(*args, **kwargs)
            is_execute = _is_execute_cycle_func(resp, condition=condition)
            api_name = func.__name__
            if is_execute:
                logger.info(f"==========<{api_name}>被指定为依赖接口,将响应结果存储为全局变量==========")
                api_info = {
                    "name": api_name,
                    "module": _get_module_name_by_method_obj(func),
                    "ao": eval(f'args[0].{api_name}.__self__.__name__')  # 类方法首个位置参数始终为类实例
                }
                if jsonpath_expr:
                    cache.update(var_name, get_value_by_jsonpath(jsonpath_expr, resp)) if cache.get(var_name) else cache.set(var_name, get_value_by_jsonpath(jsonpath_expr, resp), api_info=api_info)
                else:
                    cache.update(var_name, resp) if cache.get(var_name) else cache.set(var_name, resp, api_info=api_info)
                logger.info(f"==========<{api_name}>存储全局变量{var_name}完成==========")
            else:
                logger.info(
                    f"==========<{api_name}>已被调用，但响应结果不满足传入条件,不对{var_name}进行存储==========")
            return resp

        return wrapper

    return decorator


def async_api(cycle_func: Callable, jsonpath_expr: Union[Text, List], expr_index=0, condition: Union[Dict, bool] = None,
              *out_args,
              **out_kwargs):
    """
    异步接口装饰器
    目标接口请求完成后，根据jsonpath表达式从其响应结果中提取异步任务id，
    然后将异步任务id传给轮询函数

    :param cycle_func: 轮询函数
    :param jsonpath_expr: 异步任务id提取表达式
    :param expr_index: jsonpath提取索引，默认为0; 传入':'，获取整个list
    :param condition: 是否执行轮询函数的条件，默认执行。如果传了condition，那么当满足condition时执行cycle_func，不满足不执行。
            example1(condition为dict)：
                condition = {"expr":"ret_code","expected_value":0}
                当返回值中的ret_code == 0时，会去执行cycle_func进行异步任务检查，反之不执行。
            example2(condition为bool):
                condition = (1+1 == 2)
                执行cycle_func；
                condition = False
                不执行cycle_func
    :return:
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            resp = func(*args, **kwargs)
            is_execute = _is_execute_cycle_func(resp, condition=condition)
            if is_execute:
                job_id = _handle_jsonpath_extract(resp, jsonpath_expr, expr_index=expr_index)
                if job_id is None:
                    if condition is None:
                        raise JsonPathExtractFailed(res=resp, jsonpath_expr=jsonpath_expr)
                    return resp

                logger.info(
                    f"==========后置异步接口断言开始<{func.__name__}>: 轮询函数<{cycle_func.__name__}>==========")
                async_res = cycle_func(job_id, *out_args, **out_kwargs)
                resp.setdefault("async_res", [])
                if async_res:
                    async_res_list = async_res if isinstance(async_res, list) else [async_res]
                    resp["async_res"].extend(async_res_list)
                logger.info(f"==========后置异步接口断言结束<{func.__name__}>==========")
            else:
                logger.info(f"==========后置异步接口不满足执行条件，不执行<{func.__name__}>==========")
            return resp

        return wrapper

    return decorator


def update(var_name: Text, *out_args, **out_kwargs):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            resp = func(*args, **kwargs)
            api_name = func.__name__
            if cache.get(var_name):
                logger.info(f"==========cache变量<{var_name}>开始更新==========")
                api_info = cache.get(var_name, select_field="api_info")
                dependence_res = _call_dependence_for_update(api_info, *out_args, **out_kwargs)
                cache.update(var_name, dependence_res)
                logger.info(f"==========<{api_name}>cache更新<{api_info.get('name')}>结束==========")
            return resp

        return wrapper

    return decorator


def command(name, **out_kwargs):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            from aomaker.cli import main, OptionHandler
            cmd = main.get_command(None, 'run')
            option_handler = OptionHandler()
            option_handler.add_option(name, **out_kwargs)
            cmd.params.append(click.Option(option_handler.options.pop("name"), **option_handler.options))
            new_name = name.replace("-", "")
            cli_hook.register(func, new_name)

        return wrapper

    return decorator


def hook(func):
    @wraps(func)
    def wrapper():
        session_hook.register(func)

    return wrapper


def data_maker(file_path: str, class_name: str, method_name: str) -> List[Dict]:
    """
    从测试数据文件中读取文件，构造数据驱动的列表参数
    :param file_path: 测试数据文件（相对路径，相对项目根目录）
    :param class_name: 类名
    :param method_name: 方法名
    :return:
            eg:
            [{"name":"zz"},{"name":"yy"},...]
    """
    yaml_path = os.path.join(BASEDIR, file_path)
    if not os.path.exists(yaml_path):
        raise FileNotFound(yaml_path)
    class_data = _load_yaml(yaml_path).get(class_name)
    if class_data is None:
        raise YamlKeyError(file_path, class_name)
    method_data = class_data.get(method_name)
    if method_data is None:
        raise YamlKeyError(file_path, method_name)
    return method_data


def genson(data):
    """
    生成jsonschema
    :param data: json格式数据
    :return: jsonschema
    """
    builder = SchemaBuilder()
    builder.add_object(data)
    to_schema = builder.to_schema()
    return to_schema


def dataclass(cls):
    @property
    def all_fields(self):
        return self.__dict__

    cls.all_fields = all_fields

    for field_name, field_type in cls.__annotations__.items():
        if field_name not in cls.__dict__:
            # 跳过必须字段
            continue
        if field_type is list:
            default_value = getattr(cls, field_name, [])
            if default_value is not None:
                setattr(cls, field_name, field(default_factory=lambda: list(default_value)))
        elif field_type is dict:
            default_value = getattr(cls, field_name, {})
            if default_value is not None:
                setattr(cls, field_name, field(default_factory=lambda: dict(default_value)))
    return dc(cls)


def _call_dependence(dependent_api: Callable or Text, api_name: Text, imp_module, *out_args,
                     **out_kwargs) -> Tuple:
    if isinstance(dependent_api, str):
        # 同一个类下的接口
        class_, method_ = _parse_dependent_api(dependent_api)
        try:
            exec(f'from {imp_module} import {class_}')
        except ModuleNotFoundError as mne:
            logger.error(f"导入模块{imp_module}未找到，请确保imp_module传入参数正确")
            raise mne
        except ImportError as ie:
            logger.error(f"导入ao对象错误：{class_}，请确保dependence传入参数正确")
            raise ie
        except SyntaxError as se:
            logger.error(f"dependence传入imp_module参数错误，imp_module={imp_module} ")
            raise se
        depend_api_name = eval(f"{class_}.{method_}.__name__")
        logger.info(f"==========<{api_name}>前置依赖<{depend_api_name}>执行==========")
        try:
            res = eval(f'{class_}.{method_}(*{out_args}, **{out_kwargs})')
        except TypeError as te:
            logger.error(f"dependence参数传递错误，错误参数：{dependent_api}")
            raise te
        depend_api_info = {"name": method_, "module": imp_module, "ao": class_.lower()}
    else:
        # 不同类下的接口
        depend_api_name = dependent_api.__name__
        logger.info(f"==========<{api_name}>前置依赖<{depend_api_name}>执行==========")
        res = dependent_api(*out_args, **out_kwargs)
        depend_api_info = {"name": depend_api_name, "module": _get_module_name_by_method_obj(dependent_api),
                           "ao": type(dependent_api.__self__).__name__.lower()}
    return res, depend_api_info


def _call_dependence_for_update(api_info: Dict, *out_args, **out_kwargs) -> Dict:
    api_name = api_info.get("name")
    api_module = api_info.get("module")
    module = importlib.import_module(api_module)
    try:
        ao = getattr(module, api_info.get("ao"))
    except AttributeError as e:
        logger.error(f"在{api_module}中未找到ao对象<{api_info.get('ao')}>！")
        raise e
    res = getattr(ao, api_name)(*out_args, **out_kwargs)
    return res


def _extract_by_jsonpath(source: Text, jsonpath_expr: Text, index: int):
    target = jsonpath(source, jsonpath_expr)[index]
    return target


def _parse_dependent_api(dependent_api):
    try:
        class_, method_ = dependent_api.split('.')
    except ValueError as ve:
        logger.error(f"dependence参数传递错误，错误参数：{dependent_api}")
        raise ve
    else:
        return class_, method_


def _load_yaml(yaml_file):
    with open(yaml_file, encoding='utf-8') as f:
        yaml_testcase = yaml.safe_load(f)
    return yaml_testcase


def _get_module_name_by_method_obj(method_obj) -> Text:
    """
    return: x.y.z
    """
    module_name = method_obj.__module__
    module_path = importlib.import_module(module_name).__file__
    cur_dir = os.path.abspath('.')
    rel_path = os.path.relpath(module_path, cur_dir)
    module_name = os.path.splitext(rel_path)[0].replace(os.path.sep, '.')
    return module_name


def _handle_jsonpath_extract(resp, jsonpath_expr, expr_index=0):
    if isinstance(jsonpath_expr, str):
        jsonpath_expr = [jsonpath_expr]

    for expr in jsonpath_expr:
        extract_res = jsonpath(resp, expr)
        if extract_res:
            return extract_res if expr_index == ":" else extract_res[expr_index]

    # raise JsonPathExtractFailed(res=resp, jsonpath_expr=jsonpath_expr)


def _is_execute_cycle_func(res, condition=None) -> bool:
    if condition is None:
        return True

    if isinstance(condition, bool):
        return condition

    data = ExecuteAsyncJobCondition(**condition)
    expr = data.expr
    expected_value = data.expected_value
    res = jsonpath(res, expr)
    if res is False:
        raise JsonPathExtractFailed(res=res, jsonpath_expr=expr)
    if res[0] == expected_value:
        return True
    return False


def kwargs_handle(cls):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if kwargs:
                if not kwargs.get('body'):
                    kwargs['body'] = {}
                if not kwargs.get('data'):
                    kwargs['data'] = {}
                if not kwargs.get('params'):
                    kwargs['params'] = {}
            return func(*args, **kwargs)

        return wrapper

    for attr_name, attr_value in cls.__dict__.items():
        if callable(attr_value):
            setattr(cls, attr_name, decorator(attr_value))
    return cls


def get_key_index(data):
    data = list(data.items())
    for i in range(len(data)):
        kv_set = data[i]
        if not isinstance(kv_set[1], NoneType) and not isinstance(kv_set[1], list) and not isinstance(kv_set[1], dict):
            return i
    raise KeyError("没有找到非空非Dict的key")

def compare_two_dict(expectedDict: dict, aimDict: dict) -> Optional[dict]:
    """
    朴实无华的匹配算法
    :param expectedDict:预期结果
    :param aimDict: 实际结果
    :return: 若匹配异常则返回assert_exception_detail失败详情，否则返回None
    """
    assert_exception_detail = dict()
    try:
        for k, v in expectedDict.items():
            if k not in aimDict:  # 实际值缺少这个key直接结束匹配
                raise CompareException(f'缺少key:【{k}】', k, "not found key")
            else:
                if isinstance(v, dict):  # v为字典时进入此逻辑
                    if type(v) != type(aimDict.get(k)):  # 如果实际值类型不与预期一致，结束匹配
                        raise CompareException(f'【{k}】值类型有误', str(type(v)), str(type(aimDict.get(k))))
                    tmp = compare_two_dict(v, aimDict.get(k))
                    if tmp is not None and len(tmp) > 0:  # 递归对实际值进行匹配
                        raise CompareException(tmp["reason"], tmp["excepted"], tmp["real_result"])
                elif isinstance(v, list):  # v为列表时进入此逻辑
                    if type(v) != type(aimDict.get(k)):  # 如果实际值类型不与预期一致，结束匹配
                        raise CompareException(f'【{k}】值类型有误', str(type(v)), str(type(aimDict.get(k))))
                    if len(v) > 0 and isinstance(v[0], dict):  # 若list中为dict，则以dict中第一个非空非dict非list的键值对预期值进行排序
                        sort_key_index = get_key_index(v[0])
                        v.sort(key=lambda x: list(x.items())[sort_key_index])
                    else:
                        v.sort()  # 非dict正常排序
                    if len(aimDict.get(k)) > 0 and isinstance(aimDict.get(k)[0], dict):  # 若list中为dict，则以dict中第一个非空非dict非list的键值对预期值进行排序
                        sort_key_index = get_key_index(v[0])
                        aimDict.get(k).sort(key=lambda x: list(x.items())[sort_key_index])
                    else:
                        aimDict.get(k).sort()  # 非dict正常排序
                    count = len(v)
                    actual_count = len(aimDict.get(k))
                    if count != actual_count:  # 对比预期值和实际值list长度，不一致则结束匹配
                        raise CompareException(f'【{k}】值数组长度有误', str(count), str(actual_count))
                    for i in range(0, count):  # 经过排序后预期值与实际值中对顺序应已一致，故直接一对一匹配
                        ev = v[i]
                        av = aimDict.get(k)[i]
                        if isinstance(ev, dict):  # 元素若为dict则进行递归
                            tmp = compare_two_dict(ev, av)
                            if tmp is not None and len(tmp) > 0:
                                raise CompareException(tmp["reason"], tmp["excepted"], tmp["real_result"])
                        else:  # 非dict正常一对一匹配
                            if ev != av:
                                raise CompareException(f'【{k}】值有误', str(v), str(aimDict.get(k)))
                else:  # 不为list或dict则对比值
                    if v != aimDict.get(k):
                        raise CompareException(f'【{k}】值有误', str(v), str(aimDict.get(k)))
    except CompareException as e:
        reason, excepted, real_result = e.args  # 记录失败对reason、预期值、实际值
        assert_exception_detail['reason'] = reason
        assert_exception_detail['excepted'] = excepted
        assert_exception_detail['real_result'] = real_result
        print(assert_exception_detail)
    return assert_exception_detail if len(assert_exception_detail) > 0 else None  # 若有异常则返回异常详情，否则返回空


if __name__ == '__main__':
    x = data_maker('aomaker/data/api_data/job.yaml', 'job', 'submit_job')
    print(x)

