import os, sys
import pandas as pd
import time, re
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
error_stat_file_path = f'{result_root}/error_stat_display.csv'
py_log_file = f'{result_dir_root}/test_postprocess.log'
if os.path.exists(py_log_file):
    os.remove(py_log_file)
logging.basicConfig(filename=py_log_file, level=logging.INFO)


def fix_symbol_not_found_test():
    print()


def filter_bug_irrelative_tests():
    print()


if __name__ == '__main__':
    print()