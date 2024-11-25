# --coding:utf-8--
from typing import Any

from jsonpath import jsonpath
from jsonschema import validate, ValidationError

from aomaker.log import logger
from aomaker.cache import Schema
from aomaker.exceptions import SchemaNotFound, CaseError


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
            raise e

    @staticmethod
    def assert_gt(actual_value, expected_value, msg: str = ""):
        """
        greater than
        """
        try:
            assert actual_value > expected_value, msg
        except AssertionError as e:
            logger.error(f"gt断言失败，预期结果：{expected_value}，实际结果：{actual_value}，message：{msg}")
            raise e

    @staticmethod
    def assert_lt(actual_value, expected_value, msg: str = None):
        """
        less than
        """
        try:
            assert actual_value < expected_value, msg
        except AssertionError as e:
            logger.error(f"lt断言失败，预期结果：{expected_value}，实际结果：{actual_value}，message：{msg}")
            raise e

    @staticmethod
    def assert_neq(actual_value, expected_value, msg: str = ""):
        """
        not equals
        """
        try:
            assert actual_value != expected_value, msg
        except AssertionError as e:
            logger.error(f"neq断言失败，预期结果：{expected_value}，实际结果：{actual_value}，message：{msg}")
            raise e

    @staticmethod
    def assert_ge(actual_value, expected_value, msg: str = ""):
        """
        greater than or equals
        """
        try:
            assert actual_value >= expected_value, msg
        except AssertionError as e:
            logger.error(f"ge断言失败，预期结果：{expected_value}，实际结果：{actual_value}，message：{msg}")
            raise e

    @staticmethod
    def assert_le(actual_value, expected_value, msg: str = ""):
        """
        less than or equals
        """
        try:
            assert actual_value <= expected_value, msg
        except AssertionError as e:
            logger.error(f"le断言失败，预期结果：{expected_value}，实际结果：{actual_value}，message：{msg}")
            raise e

    @staticmethod
    def assert_contains(actual_value, expected_value, msg: str = ""):
        assert isinstance(
            expected_value, (list, tuple, dict, str, bytes)
        ), "expect_value should be list/tuple/dict/str/bytes type"
        try:
            assert expected_value in actual_value, msg
        except AssertionError as e:
            logger.error(f"contains断言失败，预期结果：{expected_value}，实际结果：{actual_value}，message：{msg}")
            raise e

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
            raise e

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
            raise e

    def func_assert(self, expected: dict, resp: Any = None, **others):
        funcs = expected.keys()
        if any(item in funcs for item in ['eq', 'neq', 'gt', 'ge', 'lt', 'le']) and not hasattr(resp, '__getitem__'):
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
            'condition': eval
        }
        for key, info in expected.items():
            msg = info[-1] if len(info) == 3 else ""
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
                case _:
                    raise CaseError(f'无效类型断言: {key}')
