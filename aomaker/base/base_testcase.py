# --coding:utf-8--
import json
from json import JSONDecodeError
from typing import Any

from jsonpath import jsonpath
from jsonschema import validate, ValidationError

from aomaker.log import logger
from aomaker.cache import Schema
from aomaker._aomaker import compare_two_dict
from aomaker.exceptions import SchemaNotFound, CaseError, CompareException


class BaseTestcase:

    @staticmethod
    def assert_eq(actual_value, expected_value, msg: str = ""):
        """
        equals
        """
        try:
            assert actual_value == expected_value, msg
        except AssertionError as e:
            logger.error(f"eq断言失败，预期结果：{expected_value}，实际结果：{actual_value}，message：{msg}")
            raise AssertionError(f"eq断言失败，预期结果：{expected_value}，实际结果：{actual_value}，message：{msg}")

    @staticmethod
    def assert_gt(actual_value, expected_value, msg: str = ""):
        """
        greater than
        """
        try:
            assert actual_value > expected_value, msg
        except AssertionError as e:
            logger.error(f"gt断言失败，预期结果：{expected_value}，实际结果：{actual_value}，message：{msg}")
            raise AssertionError(f"gt断言失败，预期结果：{expected_value}，实际结果：{actual_value}，message：{msg}")

    @staticmethod
    def assert_lt(actual_value, expected_value, msg: str = None):
        """
        less than
        """
        try:
            assert actual_value < expected_value, msg
        except AssertionError as e:
            logger.error(f"lt断言失败，预期结果：{expected_value}，实际结果：{actual_value}，message：{msg}")
            raise AssertionError(f"lt断言失败，预期结果：{expected_value}，实际结果：{actual_value}，message：{msg}")

    @staticmethod
    def assert_neq(actual_value, expected_value, msg: str = ""):
        """
        not equals
        """
        try:
            assert actual_value != expected_value, msg
        except AssertionError as e:
            logger.error(f"neq断言失败，预期结果：{expected_value}，实际结果：{actual_value}，message：{msg}")
            raise AssertionError(f"neq断言失败，预期结果：{expected_value}，实际结果：{actual_value}，message：{msg}")

    @staticmethod
    def assert_ge(actual_value, expected_value, msg: str = ""):
        """
        greater than or equals
        """
        try:
            assert actual_value >= expected_value, msg
        except AssertionError as e:
            logger.error(f"ge断言失败，预期结果：{expected_value}，实际结果：{actual_value}，message：{msg}")
            raise AssertionError(f"ge断言失败，预期结果：{expected_value}，实际结果：{actual_value}，message：{msg}")

    @staticmethod
    def assert_le(actual_value, expected_value, msg: str = ""):
        """
        less than or equals
        """
        try:
            assert actual_value <= expected_value, msg
        except AssertionError as e:
            logger.error(f"le断言失败，预期结果：{expected_value}，实际结果：{actual_value}，message：{msg}")
            raise AssertionError(f"le断言失败，预期结果：{expected_value}，实际结果：{actual_value}，message：{msg}")

    @staticmethod
    def assert_contains(actual_value, expected_value, msg: str = ""):
        assert isinstance(
            expected_value, (list, tuple, dict, str, bytes)
        ), "expect_value should be list/tuple/dict/str/bytes type"
        try:
            assert expected_value in actual_value, msg
        except AssertionError as e:
            logger.error(f"contains断言失败，预期结果：{expected_value}，实际结果：{actual_value}，message：{msg}")
            raise AssertionError(f"contains断言失败，预期结果：{expected_value}，实际结果：{actual_value}，message：{msg}")

    @staticmethod
    def assert_schema(instance, api_name):
        """
        Assert JSON Schema
        :param instance: 请求响应结果
        :param api_name: 存放在schema表中的对应key名
        :return:
        """
        json_schema = Schema().get(api_name)
        if json_schema is None:
            logger.error('jsonschema未找到！')
            raise SchemaNotFound(api_name)
        try:
            validate(instance, schema=json_schema)
        except ValidationError as msg:
            logger.error(msg)
            raise AssertionError

    @staticmethod
    def assert_in(actual_value, expected_value, msg: str = ""):
        assert isinstance(
            expected_value, (list, tuple, dict, str, bytes)
        ), "expected_value should be list/tuple/dict/str/bytes type"
        try:
            if isinstance(actual_value, dict) and isinstance(expected_value, dict):
                assert all(
                    key in actual_value and actual_value[key] == expected_value[key] for key in expected_value), msg
            else:
                assert expected_value in actual_value, msg
        except AssertionError as e:
            logger.error(f"in断言失败，预期结果：{expected_value}，实际结果：{actual_value}，message：{msg}")
            raise AssertionError(f"in断言失败，预期结果：{expected_value}，实际结果：{actual_value}，message：{msg}")

    @staticmethod
    def assert_nin(actual_value, expected_value, msg: str = ""):
        assert isinstance(
            expected_value, (list, tuple, dict, str, bytes)
        ), "expected_value should be list/tuple/dict/str/bytes type"
        try:
            if isinstance(actual_value, dict) and isinstance(expected_value, dict):
                assert all(
                    key not in actual_value or actual_value[key] != expected_value[key] for key in expected_value), msg
            else:
                assert expected_value not in actual_value, msg
        except AssertionError as e:
            logger.error(f"nin断言失败，预期结果：{expected_value}，实际结果：{actual_value}，message：{msg}")
            raise AssertionError(f"nin断言失败，预期结果：{expected_value}，实际结果：{actual_value}，message：{msg}")

    @staticmethod
    def assert_resp_value(actual_value, expected_value, skip_key=None):
        compare_two_dict_res = compare_two_dict(expected_value, actual_value, skip_key)
        try:
            assert compare_two_dict_res is None
        except AssertionError:
            logger.error(f"resp断言失败, 响应结果不符合预期, message: {compare_two_dict_res}")
            raise AssertionError(f"resp断言失败, 响应结果不符合预期, message: {compare_two_dict_res}")

    def func_assert(self, assert_info: list[dict], resp: Any = None, **others):
        funcs = []
        for expected in assert_info:
            tmp = expected.keys()
            for t in tmp:
                funcs.append(t)
        if any(item in funcs for item in ['eq', 'neq', 'gt', 'ge', 'lt', 'le', 'resp']) and not hasattr(resp, '__getitem__'):
            raise CaseError(f'此类型断言传入的resp无法使用: funcs: {funcs}, resp: {resp}')
        assert_func = {
            'eq': self.assert_eq,
            'neq': self.assert_neq,
            'gt': self.assert_gt,
            'ge': self.assert_ge,
            'lt': self.assert_lt,
            'le': self.assert_le,
            'in': self.assert_in,
            'nin': self.assert_nin,
            'condition': eval,
            'resp': self.assert_resp_value
        }
        for expected in assert_info:
            for key, info in expected.items():
                msg = info[-1] if len(info) >= 3 else ""
                if (key in ['in', 'nin'] or (key == 'condition' and '{' in info[0])) and not others:
                    raise CaseError(f'此类型断言时需传入值替换占位符: {key}')
                match key:
                    case 'eq' | 'neq' | 'gt' | 'ge' | 'lt' | 'le':
                        actual_value = jsonpath(resp, info[0])[0]
                        assert_func[key](actual_value, info[1], msg)
                    case 'in' | 'nin':
                        try:
                            actual_value = jsonpath(resp, info[0])[0]
                        except Exception as e:
                            logger.info(f'无法解析为jsonpath: {info[0]}, err_msg: {e}')
                            try:
                                actual_value = others[info[0]]
                            except KeyError:
                                raise CaseError(f'此类型断言下没有传入对应实际值: {key}')
                        assert_func[key](actual_value, info[1], msg)
                    case 'condition':
                        try:
                            actual_value = assert_func[key](info[0].format(**others))
                        except Exception as e:
                            raise CaseError(f'语句执行失败: {e}')
                        if not isinstance(actual_value, bool):
                            raise CaseError(f'此类型下执行的语句需要为条件语句: {info[0].format(**others)}')
                        assert actual_value == info[1], msg
                    case 'resp':
                        actual_value = jsonpath(resp, info[0])[0]
                        if not isinstance(info[1], str):
                            raise CaseError(f'此类型下需传入预期响应结果的转义字符串')
                        try:
                            expected_value = json.loads(info[1])
                            skip_key = info[-1] if len(info) >= 3 else None
                            assert_func[key](actual_value, expected_value, skip_key)
                        except JSONDecodeError as e:
                            raise CaseError(f'尝试装换传入值为dict失败,msg:{e}')
                        except CompareException as e:
                            raise CaseError(e.args[0] + f"\nResp: {resp}")
                    case _:
                        raise CaseError(f'无效类型断言: {key}')
