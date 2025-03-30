import os, sys
import pandas as pd
from tqdm import *
import time

# 默认参数
version = 'fixing' #执行测试的缺陷版本
test_prefix = 'evosuite2019' #跟结果文件存放的路径名以及inclue的Test类文件名有关

# 可以不更改的默认值
analysis_output = 'build_results.csv'

# 需要更改的目录位置
result_dir_root = '/mnt/Benchmark_py/tests_study/'# 测试结果存放路径
bugs_info = '/mnt/Benchmark_py/bugs_inputs.csv' #存放需要测试的缺陷信息

########## 以下均不要更改 ##########
result_root = f'{result_dir_root}/{version}_result/{test_prefix}'


def numeric_stat_diplay(df):
    numerics = df.select_dtypes(include=['number'])
    desc_stats = numerics.describe()
    print(desc_stats)


if __name__ == '__main__':
    tasks = tqdm(['fixing'])# 'buggy', 'fixing', 'original'
    for task in tasks:
        tasks.set_description('Processing for %s results display' % task)
        version = str(task)
        result_root = f'{result_dir_root}/{version}_result/{test_prefix}'
        analysis_result = f'{result_root}/{analysis_output}'
        df = pd.read_csv(analysis_result)
        numeric_stat_diplay(df.copy())
        print()
        time.sleep(.1)
        