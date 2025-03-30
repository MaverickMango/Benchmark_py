import os, sys
import pandas as pd
from tqdm import *
import time
import logging

# 默认参数
version = 'fixing' #执行测试的缺陷版本
test_prefix = 'evosuite2019' #跟结果文件存放的路径名以及inclue的Test类文件名有关

# 可以不更改的默认值
analysis_output = 'build_results.csv'
py_log_file_name = 'display.log'
display_output_file_sufix = '_display.csv'

# 需要更改的目录位置
result_dir_root = '/mnt/Benchmark_py/tests_study/'# 测试结果存放路径
bugs_info = '/mnt/Benchmark_py/bugs_inputs.csv' #存放需要测试的缺陷信息

########## 以下均不要更改 ##########
result_root = f'{result_dir_root}/{version}_result/{test_prefix}'


def running_stat_display(df):
    if df['build_status'].dtype == bool:
        grouped = df.groupby('proj')['build_status'].agg(
            success='sum',
            group_size='count'
        ).reset_index()
    else:
        grouped = df.groupby('proj').agg(
            success=pd.NamedAgg(column='build_status', aggfunc=lambda x: (x == True).sum()),
            group_size=pd.NamedAgg(column='build_status', aggfunc='count')
        ).reset_index()
    # total_success = grouped['success'].sum()
    # total_records = df.shape[0]
    grouped['success_rate'] = grouped['success'] / grouped['group_size']

    df_formatted = grouped.copy()
    df_formatted['success_rate'] = df_formatted['success_rate'].map(lambda x: f'{x:.2%}')
    
    output_file = f'{result_root}/build_status{display_output_file_sufix}'
    logging.info(f'按项目统计测试执行为True的结果存放在：{output_file}')
    df_formatted.to_csv(output_file, index=False)


def numeric_stat_display(df):
    stat_names = ['total_time_seconds', 'tests_run', 'test_time_elapsed_seconds']

    numerics_grouped = pivot_describe(df, ['proj', 'id'], stat_names)
    
    output_file = f'{result_root}/bug_numeric_stat{display_output_file_sufix}'
    logging.info(f'按缺陷统计数值类型数据的结果存放在：{output_file}')
    numerics_grouped.to_csv(output_file, index=False)

    numerics_grouped = pivot_describe(df, ['proj'], stat_names)
    
    output_file = f'{result_root}/proj_numeric_stat{display_output_file_sufix}'
    logging.info(f'按项目统计数值类型数据的结果存放在：{output_file}')
    numerics_grouped.to_csv(output_file, index=False)


def pivot_describe(df, groupby, describe_names):
    copyed = df.copy()
    pd.options.display.float_format = '{:,.2f}'.format
    grouped = (
        copyed.groupby(groupby)[describe_names]
        .describe(percentiles=[.25,.5,.75])
    )
    grouped.columns = grouped.columns.swaplevel(0, 1)
    level_name = f'level_{str(len(groupby))}'
    result = (
        grouped.stack(level=1, future_stack=True)
        .reset_index()
        .rename(columns={level_name: 'metric'})
    )
    result = result.sort_values(groupby)
    return result


def failure_error_stat_display(df):
    failure_condition = (
        (df['tests_failures'] != 0) |
        (df['failing_tests'].notna()) |
        (df['tests_errors'] != 0)
    )
    failures = df[failure_condition]
    
    output_file = f'{result_root}/failure_stat{display_output_file_sufix}'
    logging.info(f'有失败测试的结果存放在：{output_file}')
    failures.to_csv(output_file, index=False)
    
    error_condition = (
        (~df['build_status'])
    )
    errors = df[error_condition]
    
    output_file = f'{result_root}/error_stat{display_output_file_sufix}'
    logging.info(f'测试执行错误的结果存放在：{output_file}')
    errors.to_csv(output_file, index=False)


if __name__ == '__main__':
    tasks = tqdm(['buggy', 'fixing', 'original'])# 'buggy', 'fixing', 'original'
    displays = ['running_stat', 'numeric_stat', 'failure_error_stat']
    for task in tasks:
        tasks.set_description('Processing for %s results display' % task)
        version = str(task)
        result_root = f'{result_dir_root}/{version}_result/{test_prefix}'
        analysis_result = f'{result_root}/{analysis_output}'
        df = pd.read_csv(analysis_result)

        py_log_file = f'{result_root}/{py_log_file_name}'
        if os.path.exists(py_log_file):
            os.remove(py_log_file)
        logging.basicConfig(filename=py_log_file, level=logging.INFO)

        for display in tqdm(displays):
            func = f'{display}_display'
            globals()[func](df.copy())
        
        time.sleep(.1)
        