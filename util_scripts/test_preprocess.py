import os, sys
import javalang.tree
import pandas as pd
import re, shutil
from tqdm import *
import logging
import subprocess
import javalang
from javalang.tree import ClassDeclaration, MethodDeclaration


########## 以下均不要更改 ##########
py_log_file = '/mnt/Benchmark_py/util_scripts/log/test_preprocess.log'
if os.path.exists(py_log_file):
    os.remove(py_log_file)
logger = logging.getLogger('test_preprocess')
logger.setLevel(logging.INFO)
logger.addHandler(logging.FileHandler(filename=py_log_file))
# logging.basicConfig(filename=py_log_file, level=logging.INFO)


def filter_irrelative_tests(proj, id, tests_root, funcs, test_dir, include_pattern):
    # 复制新的测试文件目录，命名为在原本的test_prefix后增加version_defect_relative信息
    old_test_path = f'{tests_root}/{proj}/{id}/{test_dir}'
    new_test_path = f'{tests_root}_bug_relative/{proj}/{id}/{test_dir}'
    if not any(func is not None for func in funcs):
        return new_test_path
    # 修改文件内容
    try:
        for root, _, files in os.walk(old_test_path):
            for file in files:
                if not re.match(include_pattern, file):
                    continue
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except Exception as e:
                    logger.error(f'file {file_path} reading error: {str(e)}')
                    continue

                # 删除缺陷无关的测试并重构文件内容
                keep_ranges, del_count, mth_count = delete_tests_by_func_name(funcs, content, proj, id, test_dir)
                update_content = []
                for start, end in keep_ranges:
                    update_content.append(content[start:end])
                update_content = ''.join(update_content)
                if not has_remaining_tests(update_content, proj, id, test_dir):
                    logger.info(f'{proj}_{id}_{test_dir}所有测试方法均缺陷无关，跳过该测试类{test_dir}')
                    continue
                
                # 写入新目录
                new_file_path = file_path.replace(tests_root, f'{tests_root}_bug_relative')
                shutil.copytree(old_test_path, new_test_path, dirs_exist_ok=True)
                with open(new_file_path, 'w', encoding='utf-8') as f:
                    f.write(update_content)
                logger.info(f'update {proj}_{id}_{test_dir} relative tests successfully: changing {del_count} in {mth_count} test(s)')
    except Exception as e:
        logger.error(f'update tests for file {file_path} error: {str(e)}')
    return new_test_path


def get_tests(test_dir, include_pattern):
    tests_list = []
    try:
        for root, _, files in os.walk(test_dir):
            for file in files:
                if not re.match(include_pattern, file):
                    continue
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except Exception as e:
                    logger.error(f'file {file_path} reading error: {str(e)}')
                    continue

                tree = javalang.parse.parse(content)
                # 提取包名
                package = tree.package.name if tree.package else ''
                for path, node in tree.filter(ClassDeclaration):
                    for _, method_node in node.filter(MethodDeclaration):
                        if method_node.name.startswith('test'):
                            tests_list.append(f'{package}.{node.name}::{method_node.name}')
    except Exception as e:
        logger.error(f'update tests for file {file_path} error: {str(e)}')
    return tests_list



def delete_tests_by_func_name(funcs, content, proj, id, test_dir):
    tree = javalang.parse.parse(content)
    keep_ranges = []
    curr_pos = 0
    mth_count = 0
    del_count = 0
    try:
        for path, method_node in tree.filter(MethodDeclaration):
            mth_count += 1
            start_position = method_node.position
            if len(method_node.annotations) > 0:
                start_position = method_node.annotations[0].position
            start, end = get_method_end(content, start_position)

            method_body = content[start:end]
            if method_node.name not in funcs:
                del_count += 1
                keep_ranges.append((curr_pos, start - 1))
                curr_pos = end + 1
        keep_ranges.append((curr_pos, len(content)))
    except Exception as e:
        logger.error(f'{proj}_{id}_{test_dir}删除函数时出现异常：{str(e)}')
    return keep_ranges, del_count, mth_count


def has_remaining_tests(content, proj, id, test_dir):
    try:
        new_tree = javalang.parse.parse(content)
        return any(
            node.name.startswith('test')
            for _, node in new_tree.filter(MethodDeclaration)
        )
    except:
        logger.error(f'{proj}_{id}_{test_dir}删除函数后文件出现语法错误！')
        return False


def delete_tests_by_func_call(funcs, content, proj, id, test_dir):
    tree = javalang.parse.parse(content)
    keep_ranges = []
    curr_pos = 0
    mth_count = 0
    del_count = 0
    try:
        for path, method_node in tree.filter(MethodDeclaration):
            if not method_node.name.startswith('test'):
                continue

            mth_count += 1
            start_position = method_node.position
            if len(method_node.annotations) > 0:
                start_position = method_node.annotations[0].position
            start, end = get_method_end(content, start_position)

            method_body = content[start:end]
            if not contains_target_func_call(method_node, funcs):
                del_count += 1
                keep_ranges.append((curr_pos, start - 1))
                curr_pos = end + 1
        keep_ranges.append((curr_pos, len(content)))
    except Exception as e:
        logger.error(f'{proj}_{id}_{test_dir}删除函数时出现异常：{str(e)}')
    return keep_ranges, del_count, mth_count


def contains_target_func_call(method_node, funcs):
    try:
        return any(
            node.member in funcs
            for _, node in method_node.filter(javalang.tree.MethodInvocation)
        )
    except:
        return False


def get_method_end(content, position):
    line = position.line
    column = position.column
    lines = content.splitlines()
    total_chars_before = sum(len(lines[i]) + 1 for i in range(line - 1))
    column_offset = 0 # column - 1
    start = total_chars_before + column_offset
    pos = start
    while content[pos] != '{':
        pos += 1
    count = 0
    while pos < len(content):
        if content[pos] == '{': count += 1
        elif content[pos] == '}': count -= 1
        if count == 0:
            return start, pos + 1
        pos += 1
    return start, pos


def get_bug_relative_funcs(df):
    funcs_df = (
        df.drop(columns=['trigger_exceptions','buggy','original'])
        .drop_duplicates()
        .groupby(['proj', 'id'])['patch_changes']
        .apply(list).reset_index()
    )
    return funcs_df


def uncompress_randoop_tar_bz2(result_root, file_path, proj=None, id=None, test_id=None):
    # Closure-57f-randoop.1.tar.bz2
    pattern = r'(?P<proj>\S+)-(?P<id>\d+)[bf]*-randoop\.(?P<test_id>\d+)\.tar\.bz2'
    if not os.path.exists(file_path):
        print("File does not exist")
        return
    if proj is None or id is None or test_id is None:
        file_name = os.path.basename(file_path)
        if match := re.match(pattern, file_name):
            proj = match.group('proj')
            id = match.group('id')
            test_id = match.group('test_id')
    out_dir = os.path.join(result_root, 'randoop_unzip', proj, str(id))
    os.makedirs(out_dir, exist_ok=True)
    command = f'tar -jxvf {file_path} -C {out_dir}'
    print(command)
    result = subprocess.run(command, shell=True)


if __name__ == '__main__':
    # # 默认参数
    # test_prefixes = Constant.TEST_PREFIX #跟结果文件存放的路径名以及inclue的Test类文件名有关

    # 可以不更改的默认值
    log_file_name = 'logfile.txt'
    failing_output_name = 'failing_tests'
    version = 'fixing'
    include = '*.java' #如果只执行目录下指定名字的测试类则更改该参数
    include_pattern = r'*\.java$'

    # 需要更改的目录位置
    bugs_info = '/mnt/Benchmark_py/bugs_inputs.csv' #存放需要测试的缺陷信息
    tests_root = '/mnt/experiments/APCA21/RGT/2019/evosuite'# 测试文件存放路径
    util_file_path = '/mnt/Benchmark_py/util_scripts/util_infos.csv'


    # logger.info(f'running for {version}...')
    # df = pd.read_csv(util_file_path)
    # # 获取缺陷相关的测试
    # funcs_df = get_bug_relative_funcs(df)
    # for _, row in tqdm(funcs_df.iterrows()):
    #     proj = row['proj']
    #     id = row['id']
    #     test_dir_root = f'{tests_root}/{proj}/{id}'
    #     for test_prefix in test_prefixes:
    #         if 'evosuite' in test_prefix:
    #             include = '*_ESTest.java'
    #             include_pattern = r'.*_ESTest\.java$'
    #         if not os.path.exists(test_dir_root):
    #             logger.info(f'tests root {test_dir_root} does not exist!')
    #             continue
    #         patch_changes = row['patch_changes']
            # # 处理patch_changes, 只保留函数名
            # funcs = [sig.split(':')[1] for sig in patch_changes]
    #         test_dirs = [entry.name for entry in os.scandir(test_dir_root) if entry.is_dir()]
    #         # 对每个测试目录执行过滤并复制结果到新的目录
    #         for test_dir in test_dirs:
    #             # logging.info(test_dir)
    #             filter_irrelative_tests(proj, id, tests_root, funcs, test_dir)

    uncompress_randoop_tar_bz2('/mnt/experiments/APCA21/RGT/2019',
                       '/mnt/experiments/APCA21/RGT/2019/randoop/Closure/randoop/1/Closure-57f-randoop.1.tar.bz2')