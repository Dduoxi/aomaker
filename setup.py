from setuptools import setup, find_packages

setup(
    # 包的名称
    name='aomaker',

    # 包的版本
    version='2.4.15',  # 请根据实际情况调整版本号

    # 包的作者
    author='Dduoxi',

    # 包的作者邮箱
    author_email='your_email@example.com',  # 请替换为您的邮箱地址

    # 包的描述
    description='基于pytest的接口自动化测试框架',

    # 包的长描述（可以从README文件中读取）
    long_description=open('README.md').read(),

    # 包的长描述内容类型
    long_description_content_type='text/markdown',

    # 包的URL
    url='https://github.com/Dduoxi/aomaker',

    # 包的依赖
    install_requires=[
        'black==23.10.0',
        'Jinja2==3.1.2',
        'jsonpath==0.82.2',
        'loguru==0.7.2',
        'PyMySQL',
        'pytest==7.4.2',
        'PyYAML==6.0',
        'requests==2.31.0',
        'allure-pytest==2.8.24',
        'pydantic==2.10.2',
        'mitmproxy==9.0.1',
        'colorlog==6.7.0',
        'jsonschema==4.19.1',
        'genson==1.2.2',
        'click==8.1.3',
        'emoji==2.2.0',
        'click-help-colors==0.9.1',
        'tenacity==8.2.3',
        'ruamel.yaml==0.17.21'
    ],

    # 包的Python版本兼容性
    python_requires='>=3.8',

    # 包含的包和模块
    packages=find_packages(exclude=("aomaker", "aomaker.*")),

    # 包含的额外文件（例如：README、LICENSE等）
    include_package_data=True,

    # 包的入口点
    entry_points={
        'console_scripts': [
            'aomaker=aomaker.cli:main_run',  # 假设您的CLI入口在 aomaker/cli.py 的 main 函数
        ],
    },

    # 包的许可证
    license='MIT',

    # 包的分类
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],

    # 其他元数据
    keywords='api automation pytest',
)
