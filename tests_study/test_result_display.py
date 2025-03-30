import os, sys
import pandas as pd
from tqdm import *
import time
import logging

# 默认参数，会在__main__中修改
version = 'fixing' #执行测试的缺陷版本
test_prefix = 'evosuite2019' #跟结果文件存放的路径名以及inclue的Test类文件名有关

# 可以不更改的默认值(最好别改)
analysis_output = 'build_results.csv' # 传入的测试统计结果
py_log_file_name = 'display.log' # 该脚本运行的log输出文件
display_output_file_sufix = '_display.csv' # 分析结果输出的表名后缀
tasks = tqdm(['buggy', 'fixing', 'original', 'compare'])# 最后的compare是用来比较前三个不同版本得到的结果的，不要动，前面的版本可以变
displays = ['running_stat', 'numeric_stat', 'failure_error_stat'] # 希望对数据进行的分析函数，可以在下面增加函数定义然后添加到列表里，定义的函数名为f'{item[i]}_display'

# 需要更改的目录位置
result_dir_root = '/mnt/Benchmark_py/tests_study/'# 测试结果存放路径
bugs_info = '/mnt/Benchmark_py/bugs_inputs.csv' #存放需要测试的缺陷信息
trigger_test_exceptions_file_path = '/mnt/Benchmark_py/util_scripts/trigger_exceptions.csv' # 存放每个缺陷触发错误的exception

########## 以下均不要更改 ##########
result_root = f'{result_dir_root}/{version}_result/{test_prefix}'
py_log_file = f'{result_dir_root}/{py_log_file_name}'
if os.path.exists(py_log_file):
    os.remove(py_log_file)
logging.basicConfig(filename=py_log_file, level=logging.INFO)


def running_stat_display(df):
    if df['build_status'].dtype == bool:
        grouped = df.groupby('proj')['build_status'].agg(
            success='sum',
            test_class_num='count'
        ).reset_index()
    else:
        grouped = df.groupby('proj').agg(
            success=pd.NamedAgg(column='build_status', aggfunc=lambda x: (x == True).sum()),
            test_class_num=pd.NamedAgg(column='build_status', aggfunc='count')
        ).reset_index()
    # total_success = grouped['success'].sum()
    # total_records = df.shape[0]
    grouped['success_rate'] = grouped['success'] / grouped['test_class_num']

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
        (df['build_status']) &
        ((df['tests_failures'] != 0) |
        (df['failing_tests'].notna()) |
        (df['tests_errors'] != 0))
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


def different_version_compare(version_dfs):
    if os.path.exists(trigger_test_exceptions_file_path):
        # 揭错测试：build_status=True and failing_tests=trigger_tests
        buggy = [item for item in version_dfs if item['version'] == 'buggy']
        buggy_df = buggy[0]['df'] if len(buggy) > 0 else None
        if buggy_df is not None:
            failure_condition = (
                (buggy_df['build_status']) &
                ((buggy_df['tests_failures'] != 0) |
                (buggy_df['failing_tests'].notna()))
            )
            selected_names = ['proj', 'id', 'test', 'failing_tests']
            failures = buggy_df[failure_condition][selected_names]

            triggers_df = pd.read_csv(trigger_test_exceptions_file_path)
            merged = failures.merge(triggers_df[['proj', 'id', 'trigger_exceptions']], on=['proj', 'id'], how='left', suffixes=('', '_trigger'))
            merged['is_same'] = merged['failing_tests'] == merged['trigger_exceptions']
            total = len(merged)
            same_count = merged['is_same'].sum()
            same_rate = (same_count / total) * 100
            logging.info(f'所有生成的测试中是揭错测试的有：{same_count}/{total}, {same_rate}')
    print()


if __name__ == '__main__':
    result_dfs = []
    for task in tasks:
        tasks.set_description('Processing for %s results display' % task)
        version = str(task)
        logging.info(f'running for {version}...')
        if task == 'compare':
            different_version_compare(result_dfs)
        else:
            result_root = f'{result_dir_root}/{version}_result/{test_prefix}'
            analysis_result = f'{result_root}/{analysis_output}'
            df = pd.read_csv(analysis_result)
            result_dfs.append({'version': version,'df': df.copy()})

            for display in tqdm(displays):
                func = f'{display}_display'
                globals()[func](df.copy())
            
            time.sleep(.1)
    
        