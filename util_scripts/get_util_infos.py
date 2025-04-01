import os, sys
import json, re
import pandas as pd
from tqdm import *
import time
import logging

# 可以不更改的默认值(最好别改)
py_log_file_name = 'util_infos.log' # 该脚本运行的log输出文件

# 需要更改的目录位置
# /mnt/Benchmark/data/changesInfo/Math_2/properties/mappings/b2o
info_root = '/mnt/Benchmark/data/changesInfo/' # json文件存放根目录
result_dir_root = '/mnt/Benchmark_py/util_scripts'# 测试结果存放路径
bugs_info = '/mnt/Benchmark_py/bugs_inputs.csv' #存放需要测试的缺陷信息
original_config_path = '/mnt/experiments/bugs/{proj}/{proj}_{id}_original/.defects4j.config'

########## 以下均不要更改 ##########
result_root = f'{result_dir_root}'
json_file_name = 'origianl_fixing_info.json'
mapping_file_name = 'properties/mappings/b2o'
log_path = f'{result_root}/log/{py_log_file_name}'
if os.path.exists(log_path):
    os.remove(log_path)
logging.basicConfig(filename=log_path, level=logging.INFO)


def parse_json(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except json.JSONDecodeError:
        logging.error(f'json 文件{file_path}解析错误, 格式不正确。')
        return []


def get_exception(data):
    #提取trigger_tests中的exception的值
    trigger_exceptions = {
        'trigger_exceptions': None
    }
    try:
        trigger_tests = data.get('trigger_tests', [])
        exps = []
        for test in trigger_tests:
            exps.append(test['exception'])
        trigger_exceptions['trigger_exceptions'] = '#'.join(exps)
        return trigger_exceptions
    except AttributeError:
        logging.error(f'json 文件格式与预期不符，数据提取错误。')
        return trigger_exceptions


def get_buggy_dirs(data):
    root_dirs = {
        'src.dir': None,
        'test.dir': None
    }
    try:
        properties = data.get('properties', {'src.dir': None,'test.dir': None})
        root_dirs['src.dir'] = properties['src.dir']
        root_dirs['test.dir'] = properties['test.dir']
        return root_dirs
    except AttributeError:
        logging.error(f'json 文件格式与预期不符，数据提取错误。')
        return root_dirs


def get_original_dirs(file_path):
    root_dirs = {
        'src.dir': None,
        'test.dir': None
    }
    if not os.path.exists(file_path):
        return root_dirs
    try:
        src_pattern = re.compile(
            r'^d4j\.dir\.src\.classes\s*=\s*(.+)$',
            re.MULTILINE
        )
        test_pattern = re.compile(
            r'^d4j\.dir\.src\.tests\s*=\s*(.+)$',
            re.MULTILINE
        )
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        src_match = src_pattern.search(content)
        test_match = test_pattern.search(content)
        if src_match:
            root_dirs['src.dir'] = src_match.group(1).strip()
        if test_match:
            root_dirs['test.dir'] = test_match.group(1).strip()
        return root_dirs
    except Exception as e:
        logging.error(f'数据提取错误: {str(e)}')
        return root_dirs


def find_change(buggy_dicts, original_dicts, file_path):
    results = []
    if not os.path.exists(file_path):
        return results
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line.startswith('R'):
                continue
            parts = line.split('\t')
            if len(parts) < 3:
                continue
            _, buggy, original = parts
            if not buggy_dicts['src.dir'] or (not buggy.startswith(buggy_dicts['src.dir']) and not buggy.startswith(buggy_dicts['test.dir'])):
                continue

            # 截取src或者test的目录
            buggy = buggy.removeprefix(f'{buggy_dicts['src.dir']}/')
            buggy = buggy.removeprefix(f'{buggy_dicts['test.dir']}/')
            original = original.removeprefix(f'{original_dicts['src.dir']}/')
            original = original.removeprefix(f'{original_dicts['test.dir']}/')

            buggy_name = os.path.basename(buggy)
            original_name = os.path.basename(original)
            if buggy_name != original_name:
                continue
            
            buggy_dirs = os.path.dirname(buggy).split('/')
            rev_b = buggy_dirs[::-1]
            original_dirs = os.path.dirname(original).split('/')
            rev_o = original_dirs[::-1]
            min_len = min(len(rev_b), len(rev_o))
            diff_index = None
            for i in range(min_len):
                if rev_b[i] != rev_o[i]:
                    diff_index = i
                    break
            if diff_index is None:
                continue
            buggy_path = '/'.join(buggy_dirs[:len(buggy_dirs) - diff_index])
            original_path = '/'.join(original_dirs[:len(original_dirs) - diff_index])
            results.append({'buggy': buggy_path, 'original': original_path})
            # break
    return results


if __name__ == '__main__':
    df = pd.read_csv(bugs_info)
    proj_bugs = [item for item in df['bug_name'].tolist()]

    rows = []
    for proj_bug in tqdm(proj_bugs):
        proj = proj_bug.split('_')[0]
        id = proj_bug.split('_')[1]

        config_path = original_config_path.format(proj=proj, id=id)
        if not os.path.exists(config_path):
            continue
        json_file_path = f'{info_root}/{proj}_{id}/{json_file_name}'
        if not os.path.exists(json_file_path):
            continue
        index = {
            'proj': proj,
            'id': id
        }
        data = parse_json(json_file_path)
        exps = get_exception(data)
        index = index | exps
        buggy_dirs = get_buggy_dirs(data)
        original_dirs = get_original_dirs(config_path)
        # index = index | dirs

        mapping_file_path = f'{info_root}/{proj}_{id}/{mapping_file_name}'
        mappings = find_change(buggy_dirs, original_dirs, mapping_file_path)

        if len(mappings) == 0:
            index['buggy'] = None
            index['original'] = None
            rows.append(index)
        else:
            for mapping in mappings:
                result = index | mapping
                rows.append(result)
        time.sleep(.1)
    result_df = pd.DataFrame(rows)
    result_df = result_df.drop_duplicates() # 去重
    output_file = f'{result_root}/util_infos.csv'
    logging.info(f'util_info的结果存放在：{output_file}')
    result_df.to_csv(output_file, index=False)