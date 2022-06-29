# --coding:utf-8--

import sys
from functools import singledispatchmethod

# debug使用


sys.path.insert(0, 'D:\\项目列表\\aomaker')
import os
from multiprocessing import Pool
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED

import pytest

from aomaker.utils.handle_conf import HandleConf
from aomaker.fixture import SetUpSession, TearDownSession
from aomaker.log import logger


def fixture_session(func):
    """全局夹具装饰器"""

    def wrapper(*args, **kwargs):
        # 前置
        SetUpSession().set_session_vars()
        r = func(*args, **kwargs)
        TearDownSession().clear_env()
        return r

    return wrapper


class Runner:
    @fixture_session
    def run(self, args: list):
        print('run args:', args)
        pytest.main(args)
        self.gen_allure()

    @staticmethod
    def make_testsuite_path(path: str) -> list:
        path_list = [path for path in os.listdir(path) if "__" not in path]
        testsuite = []
        for p in path_list:
            testsuite_path = os.path.join(path, p)
            if os.path.isdir(testsuite_path):
                testsuite.append(testsuite_path)

        return testsuite

    @staticmethod
    def make_testfile_path(path: str) -> list:
        path_list = [path for path in os.listdir(path) if "__" not in path]
        testfile_path_list = []
        for p in path_list:
            testfile_path = os.path.join(path, p)
            if os.path.isfile(testfile_path):
                testfile_path_list.append(testfile_path)
        print(testfile_path_list)
        return testfile_path_list

    @singledispatchmethod
    def make_task_args(self, arg):
        raise TypeError("arg type must be List or Path")

    @make_task_args.register(list)
    def _(self, arg: list) -> list:
        """dist_mode:mark"""
        return arg

    @make_task_args.register(str)
    def _(self, arg: str) -> list:
        """dist_mode:suite"""
        path_list = self.make_testsuite_path(arg)
        return path_list

    @make_task_args.register(dict)
    def _(self, arg: dict) -> list:
        """dist_mode:file"""
        path_list = self.make_testfile_path(arg["path"])
        return path_list

    @staticmethod
    def gen_allure(is_clear=True):
        # todo: 测试
        cmd = 'allure generate ./tttttttt/reports/json -o ./tttttttt/reports/html'
        if is_clear:
            cmd = cmd + ' -c'
        os.system(cmd)


class ProcessesRunner(Runner):

    def main_task(self, args):
        print('run args:', args)
        pytest.main([f'-m {args}'])

    @fixture_session
    def run(self, task_args, extra_args=None):
        if extra_args is None:
            extra_args = []
        # extra_args.append('--cache-clear')
        extra_args.append('--alluredir=tttttttt/reports/json')
        process_count = len(task_args)
        p = Pool(process_count)
        logger.info(f"<AoMaker> 多进程任务启动，进程数：{process_count}")
        for arg in make_args_group(task_args, extra_args):
            p.apply_async(main_task, args=(arg,))
        p.close()
        p.join()

        self.gen_allure()

    def _process_run(self, task_args):
        print("task_args:", task_args)
        p = Pool(len(task_args))
        for task_arg in task_args:
            p.apply_async(main_task, args=(task_arg,))
        p.close()
        p.join()
        self.gen_allure()


def main_task(args: list):
    """pytest启动"""
    print("~~~~~~~~~~~~~~~~~~~~~~~~~pytest参数：", args)
    pytest.main(args)


class ThreadsRunner(Runner):
    @fixture_session
    def run(self, task_args: list or str, extra_args=None):
        """
        多线程启动pytest任务
        :param task_args:
                list：mark标记列表
                str：测试套件或测试文件所在目录路径
        :param extra_args: pytest其它参数列表
        :return:
        """
        if extra_args is None:
            extra_args = []

        extra_args.append('--alluredir=tttttttt/reports/json')
        task_args = self.make_task_args(task_args)
        thread_count = len(task_args)
        tp = ThreadPoolExecutor(max_workers=thread_count)
        logger.info(f"<AoMaker> 多线程任务启动，线程数：{thread_count}")
        _ = [tp.submit(main_task, arg) for arg in make_args_group(task_args, extra_args)]
        wait(_, return_when=ALL_COMPLETED)
        tp.shutdown()

        self.gen_allure()


def make_args_group(args: list, extra_args: list):
    """构造pytest参数列表
    pytest_args_group： [['-s','-m demo'],['-s','-m demo2'],...]
    :return pytest_args_group[-1] --> ['-s','-m demo2']
    """
    pytest_args_group = []
    for arg in args:
        pytest_args = []
        pytest_args.append(arg)
        pytest_args.extend(extra_args)
        pytest_args_group.append(pytest_args)
        yield pytest_args_group[-1]


tr = ThreadsRunner()
pr = ProcessesRunner()
# import time
# from multiprocessing import Pool
#
#
# def main_task(task_arg):
#     print(task_arg)
#     time.sleep(1)
#
#
# def process_run(task_args):
#     p = Pool(len(task_args))
#     for task_arg in task_args:
#         p.apply_async(main_task, args=(task_arg,))
#     p.close()
#     p.join()


if __name__ == '__main__':

    ProcessesRunner().run(['-m hpc', '-m ehpc', '-m ehpc1', '-m hpc1'])
