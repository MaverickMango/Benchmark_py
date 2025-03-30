import os, sys
import json
import pandas as pd
from tqdm import *
import time
import logging

# 可以不更改的默认值(最好别改)
py_log_file_name = 'trigger_tests.log' # 该脚本运行的log输出文件

# 需要更改的目录位置
info_root = '/mnt/Benchmark/data/changesInfo/' # json文件存放根目录
result_dir_root = '/mnt/Benchmark_py/'# 测试结果存放路径
bugs_info = '/mnt/Benchmark_py/bugs_inputs.csv' #存放需要测试的缺陷信息

########## 以下均不要更改 ##########
result_root = f'{result_dir_root}'
json_file_name = 'origianl_fixing_info.json'


def parse_json(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except json.JSONDecodeError:
        logging.error(f'json 文件{file_path}解析错误, 格式不正确。')
        return []


def get_exception(file_path):
    #提取trigger_tests中的exception的值
    data = parse_json(file_path)
    trigger_exceptions = []
    try:
        trigger_tests = data.get('trigger_tests', [])
        for test in trigger_tests:
            trigger_exceptions.append(test['exception'])
        return trigger_exceptions
    except AttributeError:
        logging.error(f'json 文件格式与预期不符，数据提取错误。')
        return trigger_exceptions


if __name__ == '__main__':
    df = pd.read_csv(bugs_info)
    proj_bugs = [item for item in df['bug_name'].tolist()]
    log_path = f'{result_root}/{py_log_file_name}'
    if os.path.exists(log_path):
        os.remove(log_path)
    logging.basicConfig(filename=log_path, level=logging.INFO)

    rows = []
    for proj_bug in tqdm(proj_bugs):
        proj = proj_bug.split('_')[0]
        id = proj_bug.split('_')[1]
        json_file_path = f'{info_root}/{proj}_{id}/{json_file_name}'
        if not os.path.exists(json_file_path):
            continue
        exps = get_exception(json_file_path)
        result = {
            'proj': proj,
            'id': id,
            'trigger_exceptions': '#'.join(exps)
        }
        rows.append(result)
        time.sleep(.1)
    result_df = pd.DataFrame(rows)
    output_file = f'{result_root}/trigger_exceptions.csv'
    logging.info(f'trigger_tests的exception的结果存放在：{output_file}')
    result_df.to_csv(output_file, index=False)