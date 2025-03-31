import re
import sys,os
import pandas as pd
import time
from tqdm import *
import logging

# 默认参数
version = 'fixing' #执行测试的缺陷版本
test_prefix = 'evosuite2019' #跟结果文件存放的路径名以及inclue的Test类文件名有关

# 可以不更改的默认值
log_file_name = 'logfile.txt'
failing_output_name = 'failing_tests'
analysis_output = 'build_results.csv'
tasks = tqdm(['buggy', 'fixing', 'original'])

# 需要更改的目录位置
result_dir_root = '/mnt/Benchmark_py/tests_study/'# 测试结果存放路径
bugs_info = '/mnt/Benchmark_py/bugs_inputs.csv' #存放需要测试的缺陷信息

########## 以下均不要更改 ##########
result_root = f'{result_dir_root}/{version}_result/{test_prefix}'
py_log_file = f'{result_dir_root}/analysis.log'
if os.path.exists(py_log_file):
    os.remove(py_log_file)
logging.basicConfig(filename=py_log_file, level=logging.INFO)

log_file_patterns = {
    'build_status': re.compile(r"BUILD SUCCESSFUL"),
    'total_time': re.compile(r"Total time:\s+([\d.]+)\s+second[s]?"),
    'junit_result': re.compile(
        r"\[junit\] Tests run:\s+(\d+),\s+Failures:\s+(\d+),\s+Errors:\s+(\d+),\s+Time elapsed:\s+([\d.]+)\s+sec"
    ),
    'build_error': re.compile(r"\[javac\]\s+([\d.]+)\s+error[s]?") # [javac] 2 errors
}
test_case_pattern = re.compile(r'^--- ([\w.]+)::(\w+).*')
error_pattern = re.compile(r'^\s*([\w.]+(?:Error|Exception)):')

def parse_failing(file_path):
    result = []
    if not os.path.exists(file_path):
        return result

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            count = 0
            while count < len(lines):
                line = lines[count]
                count += 1
                if not line.startswith('---'):
                    continue
                test_case_match = test_case_pattern.match(line)
                if test_case_match:
                    test_case = {
                        'class': test_case_match.group(1),
                        'method': test_case_match.group(2),
                        'exception': ''
                    }
                    next_line = lines[count]
                    count += 1
                    error_match = error_pattern.match(next_line)
                    if error_match:
                        test_case['exception'] = error_match.group(1)
                    
                    str = f'{test_case['class']}::{test_case['method']}::{test_case['exception']}'
                    result.append(str)
    except Exception as e:
        print(f'解析文件{file_path}出错: {str(e)}')
        result.append(str(e))
    return result


def parse_log(file_path):
    # print(file_path)
    result = {
        'cmd_status': False,
        'build_status': False,
        'total_time_seconds': 0,
        'tests_run': 0,
        'tests_failures': 0,
        'tests_errors': 0,
        'test_time_elapsed_seconds': 0
    }
    if not os.path.exists(file_path):
        return result
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            if len(lines) >= 2:
                result['cmd_status'] = lines[-1].strip()
            result_pattern = 'build_error'
            for line in reversed(lines):
                if log_file_patterns['build_status'].search(line):
                    result['build_status'] = True
                    result_pattern = 'junit_result'
                if match := log_file_patterns['total_time'].search(line):
                    result['total_time_seconds'] = float(match.group(1))
                if match := log_file_patterns[result_pattern].search(line):
                    if result_pattern == 'junit_result':
                        result['tests_run'] += int(match.group(1))
                        result['tests_failures'] += int(match.group(2))
                        result['tests_errors'] += int(match.group(3))
                        result['test_time_elapsed_seconds'] += float(match.group(4))
                    else:
                        result['tests_errors'] += int(match.group(1))
    except Exception as e:
        logging.error(f'解析文件{file_path}出错: {str(e)}')
        result['error'] = str(e)
    return result


def get_result():
    df = pd.read_csv(bugs_info)
    proj_bugs = [item for item in df['bug_name'].tolist()]
    rows = []
    for proj_bug in tqdm(proj_bugs):
        proj = proj_bug.split('_')[0]
        id = proj_bug.split('_')[1]
        log_files_root = f'{result_root}/{proj}/{id}'
        if not os.path.exists(log_files_root):
            continue
        test_dirs = [entry.name for entry in os.scandir(log_files_root) if entry.is_dir()]
        for test_dir in test_dirs:
            log_file_path = f'{log_files_root}/{test_dir}/{log_file_name}'
            result = parse_log(log_file_path)

            failing_file_path = f'{log_files_root}/{test_dir}/{failing_output_name}'
            failing_tests = parse_failing(failing_file_path)
            result['failing_tests'] = '#'.join(failing_tests)

            result['proj'] = proj
            result['id'] = id
            result['test'] = f'{log_files_root}/{test_dir}'.replace(f'{result_dir_root}/', '')
            
            rows.append(result)
    
    df = pd.DataFrame(rows)
    column_order = [
        'proj',
        'id',
        'test',
        'cmd_status',
        'build_status',
        'total_time_seconds',
        'tests_run',
        'tests_failures',
        'failing_tests',
        'tests_errors',
        'test_time_elapsed_seconds'
    ]
    return df[column_order]


if __name__ == '__main__':
    for task in tasks:
        tasks.set_description('Processing for %s analysis' % task)
        version = str(task)
        logging.info(f'running for {version}...')
        result_root = f'{result_dir_root}/{version}_result/{test_prefix}'
        df = get_result()

        output_file = f'{result_root}/{analysis_output}'
        logging.info(f'分析结果结果存放在：{output_file}')
        df.to_csv(output_file, index=False)
        time.sleep(.1)
        