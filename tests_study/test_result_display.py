import os, sys
import pandas as pd

from scipy.stats import fisher_exact
from scipy.stats import MonteCarloMethod
from statsmodels.stats.contingency_tables import mcnemar
from statsmodels.stats.multitest import multipletests

from tqdm import *
import time
import logging


sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from util_scripts import Constant

# 默认参数
test_prefixes = Constant.TEST_PREFIX #跟结果文件存放的路径名以及inclue的Test类文件名有关

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
py_log_file = f'{result_dir_root}/log/{py_log_file_name}'
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
    return df_formatted


def numeric_stat_display(df):
    pd.options.display.float_format = '{:,.2f}'.format
    stat_names = ['total_time_seconds', 'tests_run', 'tests_failures', 'test_time_elapsed_seconds']
    numerics = df[stat_names].describe(percentiles=[.25, .5, .75]).reset_index()
    output_file = f'{result_root}/nogroup_numeric_stat{display_output_file_sufix}'
    logging.info(f'nogroup统计数值类型数据的结果存放在：{output_file}')
    numerics.to_csv(output_file, index=False)

    numerics_grouped = pivot_describe(df, ['proj', 'id'], stat_names)
    
    output_file = f'{result_root}/bug_numeric_stat{display_output_file_sufix}'
    logging.info(f'按缺陷统计数值类型数据的结果存放在：{output_file}')
    numerics_grouped.to_csv(output_file, index=False)

    numerics_grouped = pivot_describe(df, ['proj'], stat_names)
    
    output_file = f'{result_root}/proj_numeric_stat{display_output_file_sufix}'
    logging.info(f'按项目统计数值类型数据的结果存放在：{output_file}')
    numerics_grouped.to_csv(output_file, index=False)


def pivot_describe(df, groupby, stat_names):
    copyed = df.copy()
    grouped = (
        copyed.groupby(groupby)[stat_names]
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


def failure_error_stat_display(df, output=True):
    failure_condition = (
        (df['build_status']) &
        ((df['tests_failures'] != 0) |
        (df['failing_tests'].notna()) |
        (df['tests_errors'] != 0))
    )
    failures = df[failure_condition]
    
    if output:
        output_file = f'{result_root}/failure_stat{display_output_file_sufix}'
        logging.info(f'有失败测试的结果存放在：{output_file}')
        failures.to_csv(output_file, index=False)
    
    error_condition = (
        (~df['build_status'])
    )
    errors = df[error_condition]
    
    if output:
        output_file = f'{result_root}/error_stat{display_output_file_sufix}'
        logging.info(f'测试执行错误的结果存放在：{output_file}')
        errors.to_csv(output_file, index=False)
    return failures, errors


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


def pre_process(dicts, key):
    dices = [item for item in dicts if item['version'] == key]
    df = dices[0]['df'] if len(dices) > 0 else None
    if df is None:
        return None
    df = df[df['build_status']]
    df['test'] = df['test'].str.replace(f'{key}_result/', '')
    df['tests_fail'] = df['tests_failures'] + df['tests_errors']
    df['tests_succ'] = df['tests_run'] - df['tests_fail']
    df.drop(columns=['tests_run', 'tests_failures', 'tests_errors'], inplace=True)
    return df


def hypothesis_test(version_dfs, metric='fisher_exact'):
    original_df = pre_process(version_dfs, 'original')
    fixing_df = pre_process(version_dfs, 'fixing')
    if original_df is None or fixing_df is None:
        return
    result_df = get_joins(original_df, fixing_df, metric)
    hypothesis_test_result = []
    # 通过的测试数量不分项目统计
    res = hypothesis_test_for_groupby(result_df, ['proj', 'id', 'test'], metric)
    hypothesis_test_result.extend(res)
    # 通过的测试数量按项目统计
    res = hypothesis_test_for_groupby(result_df, ['proj'], metric)
    hypothesis_test_result.extend(res)
    # 通过的测试数量按缺陷统计
    res = hypothesis_test_for_groupby(result_df, ['proj', 'id'], metric)
    hypothesis_test_result.extend(res)

    result = pd.DataFrame(hypothesis_test_result)
    output_file = f'{result_root}/hypothesis_test_{metric}_result{display_output_file_sufix}'
    logging.info(f'假设检验的结果存放在：{output_file}')
    result.to_csv(output_file, index=False)


def hypothesis_test_for_groupby(result_df, groupby, metric='fisher_exact'):
    if groupby is None:
        series = result_df.sum()
        ouput_name_prefix = 'nogroup'
    else:
        series = (
            result_df.reset_index()
            # .drop(columns=['test'])
            .groupby(groupby)
            .sum()
        )
        ouput_name_prefix = '_'.join(groupby)
    
    result_df = series.reset_index()
    output_file = f'{result_root}/{ouput_name_prefix}_{metric}_hypothesis_test_{display_output_file_sufix}'
    logging.info(f'{ouput_name_prefix}分组用于{metric}的假设检验量表的统计结果存放在：{output_file}')
    result_df.to_csv(output_file, index=False)

    return test_for_series(series, groupby, metric)


def test_for_series(series, groupby, metric='fisher_exact'):
    # 传入参数有可能是一维数组，也有可能是多维，多维情况下需要做多次检验然后再进行校正
    # 一维数组实际为一个2*2联表，多维就是多个
    # ['org_succ_fix_succ', 'org_succ_fix_fail',
    # 'org_fail_fix_succ', 'org_fail_fix_fail']
    # fail数据大多为0，所以不能用卡方……
    # 检验方法：费舍尔精确检验（Fisher's Exact Test）的Monte Carlo模拟
    if groupby is None:
        odds_ratio, p_value = globals()[f'{metric}_for_line'](series)
        print(p_value) # 哈哈哈算出来p值是1，没有显著区别那就是一致呗
        res = [{
            'group': None,
            'stat_float': odds_ratio,
            'p_value': p_value
        }]
        return res
    else:
        rows = []
        p_lists = []
        for index, row in series.iterrows():
            odds_ratio, p_value =  globals()[f'{metric}_for_line'](row)
            rows.append({
                'group': '_'.join(map(lambda x: str(x), index)) if isinstance(index, tuple) else index,
                'stat_float': odds_ratio,
                'p_value': p_value
            })
            p_lists.append(p_value)
        # todo 多次检验校正p值，这里用bh法做FDR校正
        reject, q_values, _, _ = multipletests(p_lists, method='fdr_bh')
        print(f'rejected: {reject} adjusted p_values: {q_values}')
        return rows


def fisher_exact_for_line(line):
    """
    观察矩阵如下：
            指标一  指标二
    类别一    A       B
    类别二    C       D
    """
    observed = []
    observed.append([line['A'], line['B']])
    observed.append([line['C'], line['D']])
    stat_float, p_value = fisher_exact(observed, method=MonteCarloMethod(n_resamples=10000))
    return stat_float, p_value


def mcnemar_for_line(line):
    """
    观察矩阵如下：
            指标一  指标二
    类别一    A       B
    类别二    C       D
    """
    observed = []
    observed.append([line['A'], line['B']])
    observed.append([line['C'], line['D']])
    result = mcnemar(observed, exact=False)
    return result.statistic, result.pvalue

def get_joins(org_df, fix_df, metric='fisher_exact'):
    df_index = ['proj', 'id', 'test']
    stat_index = ['tests_succ', 'tests_fail']
    org_grouped = org_df.groupby(df_index)[stat_index].sum()
    fix_grouped = fix_df.groupby(df_index)[stat_index].sum()
    merged = pd.merge(
        org_grouped,
        fix_grouped,
        on=df_index,
        suffixes=('_org', '_fix')
    )
    # 交集
    # 类别一是历史版本的通过测试数量，类别二是历史版本的失败测试数量
    # 指标一是修复版本的通过测试数量，指标二是修复版本的失败测试数量
    if metric == 'mcnemar':
        merged['A'] = merged[['tests_succ_org', 'tests_succ_fix']].min(axis=1)
        merged['B'] = merged['tests_fail_fix']
        merged['C'] = merged['tests_fail_org']
        merged['D'] = merged[['tests_fail_org', 'tests_fail_fix']].min(axis=1)
    
    # 直接看两个版本的
    # 第一行是历史版本测试执行的通过数和失败数
    # 第二行是修复版本测试执行的通过数和失败数
    if metric == 'fisher_exact':
        merged['A'] = merged['tests_succ_org']
        merged['B'] = merged['tests_fail_org']
        merged['C'] = merged['tests_succ_fix']
        merged['D'] = merged['tests_fail_fix']
    
    result = merged[
        ['A', 'B',
         'C', 'D']
    ]
    return result


if __name__ == '__main__':
    result_dfs = []
    for task in tasks:
        tasks.set_description('Processing for %s results display' % task)
        version = str(task)
        logging.info(f'running for {version}...')
        for test_prefix in test_prefixes:
            if task == 'compare':
                result_root = f'{result_dir_root}/original_result/{test_prefix}'
                different_version_compare(result_dfs)
                hypothesis_test(result_dfs)#, metric='mcnemar'
            else:
                result_root = f'{result_dir_root}/{version}_result/{test_prefix}'
                analysis_result = f'{result_root}/{analysis_output}'
                df = pd.read_csv(analysis_result)
                result_dfs.append({'version': version,'df': df.copy()})

                for display in tqdm(displays):
                    func = f'{display}_display'
                    globals()[func](df.copy())
                
                time.sleep(.1)
    
        