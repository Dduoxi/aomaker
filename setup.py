import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()
setuptools.setup(
    name='aomaker',
    version='1.0.5',
    author='Dduoxi',
    author_email='w021221@yeah.net',
    description='基于pytest的接口自动化测试框架',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/Dduoxi/aomaker',
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
    packages=setuptools.find_packages(),
    include_package_data=True,
    package_data={
        "aomaker": ["html/*.png", "html/*.html"]
    },
    entry_points={
        'console_scripts': [
            'amake=aomaker.cli:main_make_alias',
            'arun=aomaker.cli:main_arun_alias',
            'arec=aomaker.cli:main_record_alias',
            'aomaker=aomaker.cli:main',
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
