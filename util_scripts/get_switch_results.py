import os, sys
import re
import pandas as pd
from tqdm import *
import time
import logging
import switch

# 可以不更改的默认值(最好别改)
py_log_file_name = 'switch_analysis.log' # 该脚本运行的log输出文件

# 需要更改的目录位置
result_dir_root = '/mnt/Benchmark_py/tests_study/'# 测试结果存放路径
bugs_info = '/mnt/Benchmark_py/bugs_inputs.csv' #存放需要测试的缺陷信息
bugs_workdir_root = '/mnt/experiments/bugs'

########## 以下均不要更改 ##########
result_root = f'{result_dir_root}'
switch_log_file_path = f'{result_root}/original_result/switch.log'
switch_and_clean_log_root = f'{result_root}/original_result/SwitchAndClean'
switch_and_clean_log_name = 'PatchPredict.log'
output_file_path = f'{result_root}/original_result/SwitchAndClean/switch_analysis.csv'
log_path = f'{result_root}/{py_log_file_name}'
if os.path.exists(log_path):
    os.remove(log_path)
logging.basicConfig(filename=log_path, level=logging.INFO)


def get_switch_error(log_file_path):
    pattern = re.compile(
        r'Error occurred when switch (\S+)_(\d+)_original, skip this defect.'
    )
    rows = []
    try:
        with open(log_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                match = pattern.search(line.strip())
                if match:
                    proj = match.group(1)
                    id = match.group(2)
                    rows.append({'proj': proj, 'id': id})
    except Exception as e:
        logging.error(f'文件{log_file_path}解析或匹配错误：{str(e)}')
    return rows


def add_error_reason(rows):
    ere_patterns = {
        'timeout': re.compile(r'\[main\] INFO Defects4JBug - test Timeout!'),
        'build_failure': re.compile(r'BUILD FAILED')
    }
    for row in rows:
        proj = row['proj']
        id = row['id']
        row['error_reason'] = ''
        switch_and_clean_log_path = f'{switch_and_clean_log_root}/{proj}/{id}/{switch_and_clean_log_name}'
        with open(switch_and_clean_log_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in reversed(lines):
                if ere_patterns['build_failure'].search(line):
                    row['error_reason'] = 'BUILD FAILED'
                    break
                if ere_patterns['timeout'].search(line):
                    row['error_reason'] = 'TIMEOUT'
                    break


def get_switch_analysis():
    rows = get_switch_error(switch_log_file_path)
    add_error_reason(rows)
    df = pd.DataFrame(rows)
    logging.info(f'switch出错的结果存放在：{output_file_path}')
    df.to_csv(output_file_path, index=False)


def rerun():
    df = pd.read_csv(output_file_path)
    bug_info_df = pd.read_csv(bugs_info)
    for _, row in df.iterrows():
        if row['error_reason'] == 'BUILD FAILED':
            continue
        proj = row['proj']
        id = row['id']
        work_dir = f'{bugs_workdir_root}/{proj}/{id}/{proj}_{id}_original'
        sha = bug_info_df.set_index('bug_name')['originalCommit'].get(f'{proj}_{id}')
        change_res = switch.run(proj, id, 'original', work_dir, sha)
        print(change_res)
      

# [main] INFO Defects4JBug - test Timeout!
if __name__ == '__main__':
    rerun()