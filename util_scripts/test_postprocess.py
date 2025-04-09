import os, sys
import pandas as pd
import time, re
from tqdm import *
import logging


sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from util_scripts import Constant

# 默认参数
test_prefixes = Constant.TEST_PREFIX #跟结果文件存放的路径名以及inclue的Test类文件名有关

# 可以不更改的默认值
log_file_name = 'logfile.txt'
failing_output_name = 'failing_tests'
test_compile_error_output_name = 'test_compile_error.csv'
tasks = tqdm(['buggy', 'fixing', 'original'])

# 需要更改的目录位置
result_dir_root = '/mnt/Benchmark_py/tests_study/'# 测试结果存放路径
bugs_info = '/mnt/Benchmark_py/bugs_inputs.csv' #存放需要测试的缺陷信息

########## 以下均不要更改 ##########
py_log_file = f'/mnt/Benchmark_py/util_scripts/log/test_postprocess.log'
if os.path.exists(py_log_file):
    os.remove(py_log_file)
logger = logging.getLogger('test_postprocess.log')
logger.setLevel(logging.INFO)
logger.addHandler(logging.FileHandler(filename=py_log_file))
# logging.basicConfig(filename=py_log_file, level=logging.INFO)


def get_test_errors(proj, id, version, file_path):
    if not os.path.exists(file_path):
        return []
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.readlines()
    error_pattern = re.compile(
        r'\[javac\]\s+(.*?):(\d+):\s+error:\s+(.*)'
    )
    symbol_pattern = re.compile(
        r'symbol:\s+(\w+)\s+(.*)'
    )
    iterator = 0
    total_lines = len(content)
    results = []
    try:
        while iterator < total_lines:
            if error_match:= error_pattern.search(content[iterator]): 
                test_path = error_match.group(1)
                test_line = error_match.group(2)
                test_error = error_match.group(3)

                result = {
                        'proj': proj,
                        'id': id,
                        'version': version,
                        'test_path': test_path.removeprefix(tests_root),
                        'error_line': test_line,
                        'error_msg': test_error,
                        'error_symbol_type': None,
                        'error_symbol_sig': None
                    }
                if test_error == 'cannot find symbol':
                    symbol_info = None
                    for offset in range(1, 4):
                        symbol_line = content[iterator + offset].strip()
                        if symbol_match:= symbol_pattern.search(symbol_line):
                            symbol_type = symbol_match.group(1)
                            symbol_sig = symbol_match.group(2)
                            symbol_info = (symbol_type, symbol_sig)
                            break
                    if symbol_info:
                        result['error_symbol_type'] = symbol_info[0]
                        result['error_symbol_sig'] = symbol_info[1]
                        iterator += offset
                results.append(result)
            iterator += 1
    except Exception as e:
        logger.error(f'查找测试结果文件出错：{str(e)}')
    return results


def filter_uncompilable_tests(df):
    # 复制新的测试文件目录，命名为在原本的test_prefix后增加version_compile信息
    # 修改文件内容
    print()

def get_bug_irrelative_tests(error_df, defect_gt_funs):
    # 复制新的测试文件目录，命名为在原本的test_prefix后增加version_defect_relative信息
    # 修改文件内容
    print()


if __name__ == '__main__':
    for task in tasks:
        tasks.set_description('Processing for %s analysis' % task)
        version = str(task)
        logging.info(f'running for {version}...')
        
        for test_prefix in test_prefixes:
            tests_root = Constant.TESTS_ROOT[test_prefix]# 测试文件存放路径
                
            result_root = f'{result_dir_root}/{version}_result/{test_prefix}'
            error_stat_file_path = f'{result_root}/error_stat_display.csv'
            df = pd.read_csv(error_stat_file_path)
            rows = []
            for _, row in df.iterrows():
                proj = row['proj']
                id = row['id']
                test = row['test']
                log_file_path = f'{result_dir_root}/{test}/{log_file_name}'
                results = get_test_errors(proj, id, version, log_file_path)
                rows.extend(results)
            
            df = pd.DataFrame(rows)
            output_file = f'{result_root}/{test_compile_error_output_name}'
            logging.info(f'测试编译错误的结果存放在：{output_file}')
            df.to_csv(output_file, index=False)
            time.sleep(.1)