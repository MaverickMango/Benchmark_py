import os, sys
from pathlib import Path
import subprocess
import multiprocessing
import shutil
import pandas as pd
from tqdm import *
import time
import logging
import re
import xml.etree.ElementTree as ET

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from util_scripts import switch
from util_scripts import Constant
from util_scripts import test_preprocess

# 默认参数
run_tests_log_file_name = 'run_test.log'
test_prefixes = Constant.TEST_PREFIX #跟结果文件存放的路径名以及inclue的Test类文件名有关

# 可以不更改的默认值
include = '*.java' #如果只执行目录下指定名字的测试类则更改该参数
include_pattern = r'*\.java$'
log_file_name = 'logfile.txt'
failing_output_name = 'failing_tests'
tasks = tqdm(['fixing', 'original', 'buggy']) # 

# 需要更改的目录位置
tmp_dir_root = '/tmp' # 临时工作文件夹的根目录
bugs_root = '/mnt/experiments/bugs' # 下载的所有bug的根目录 缺陷目录为f'{bugs_root}/{proj}/{proj}_{id}_{version}'
result_dir_root = '/mnt/Benchmark_py/tests_study/'# 测试结果存放路径
bugs_info = '/mnt/Benchmark_py/bugs_inputs.csv' #存放需要测试的缺陷信息
util_infos_file_path = '/mnt/Benchmark_py/util_scripts/util_infos.csv' # 存放mapping结果的文件

########## 以下均不要更改 ##########
py_log_file = f'{result_dir_root}/log/{run_tests_log_file_name}'
if os.path.exists(py_log_file):
    os.remove(py_log_file)
logging.basicConfig(filename=py_log_file, level=logging.INFO)
# print(logging.getLogger().handlers[0].baseFilename)
# defects4j_root = os.getenv('DEFECTS4J_HOME')
# run_tests_cmd = '/'.join([defects4j_root, 'framework', 'bin', 'run_external_tests.pl'])
run_tests_cmd = 'defects4j external.test -p {proj} -v {id}{version} -w {work_dir} -t {test_dir_root} -i {include} -o {failing_output}'
run_tests_with_coverage_cmd = 'defects4j extTestsWithCov -w {work_dir} -t {test_dir} -s {single_test} -i {include} -o {failing_output}'
cwd = os.getcwd()


def checkout(proj, id, work_dir, version, sha=None):
    if os.path.exists(work_dir):
        return
    if version == 'original':
        version = 'o'
    elif version == 'inducing':
        version = 'i'
    elif 'bug' in version:
        version = 'b'
    elif 'fix' in version:
        version = 'f'
    else:
        version = 'b'
    logging.info(f'checking out {proj}_{id}{version}...')
    checkout_cmd = f'defects4j checkout -p {proj} -v {id}{version} -w {work_dir}'
    checkout_cmd = checkout_cmd.split(' ')
    run_cmd(cwd, checkout_cmd)
    if version == 'original':
        change_res = switch.run(proj, id, version, work_dir, sha)
        if change_res != 0:
            logging.info(f'Error occurred when switch {proj}_{id}_{version}, skip this defect.')


def run_tests(patch_changes, tmp_dir, proj, id, version, test_prefix, test_dir_root):
    test_dir = os.path.basename(test_dir_root)
    log_file = f'{result_root}/{test_prefix}/{proj}/{id}/{test_dir}/{log_file_name}'
    if os.path.exists(log_file):
        os.remove(log_file)
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    # logging.info(log_file)
    failing_output = f'{result_root}/{test_prefix}/{proj}/{id}/{test_dir}/{failing_output_name}'
    if os.path.exists(failing_output):
        os.remove(failing_output)
    last_failing_test = f'{tmp_dir}/failing-tests.txt'
    if os.path.exists(last_failing_test):
        os.remove(last_failing_test)

    if version == 'original':
        version = 'o'
        # 如果是original版本的话需要对齐包名=》复制测试目录到新的包名目录
        test_dir_root = test_dir_root.replace(tests_root, f'{tests_root}_bug_relative')
        if not os.path.exists(test_dir_root):
            return
        test_dir_root = mapping_test_dirs(proj, id, test_dir_root)
        if proj == 'Time' and os.path.exists(f'{tmp_dir}/JodaTime'):
            tmp_dir = f'{tmp_dir}/JodaTime'
    elif version == 'inducing':
        version = 'i'
        test_dir_root = test_dir_root.replace(tests_root, f'{tests_root}_bug_relative')
    elif 'fix' in version:
        version = 'f'
        # 如果是fixing版本的话，需要先执行一遍测试，收集覆盖信息，然后排除缺陷无关的测试
        test_dir_root = delete_bug_irrelative_tests(patch_changes, tmp_dir, proj, id, test_dir_root, test_dir, failing_output)
    else:
        version = 'b'
        test_dir_root = test_dir_root.replace(tests_root, f'{tests_root}_bug_relative')
    
    if not os.path.exists(test_dir_root):
        return
    # 测试工作目录，把每个版本执行的测试直接放到result里
    target_test_root = f'{result_root}/{test_prefix}/{proj}/{id}/{test_dir}'
    shutil.copytree(test_dir_root, target_test_root, dirs_exist_ok=True)
    test_dir_root = target_test_root

    logging.info(f'running tests for {proj}_{id}{version}...')
    cmd = run_tests_cmd.format(proj=proj, id=id, version=version, work_dir=tmp_dir, test_dir_root=test_dir_root, include=include, failing_output=failing_output)
    logging.info(cmd)
    cmd = cmd.split(' ')
    result = run_cmd(tmp_dir, cmd)
    if os.path.exists(last_failing_test):
        shutil.copyfile(last_failing_test, failing_output)

    # logging.info(result.stderr + result.stdout)
    if result.stdout == '0\n':
        logging.info('tests running success.')
    else:
        logging.info('tests running failied.')
    with open(log_file, 'x') as f:
        f.write(result.stderr + result.stdout)


def delete_bug_irrelative_tests(patch_changes, tmp_dir, proj, id, test_dir_root, test_dir, failing_output):
    # 获取缺陷相关的行号，处理patch_changes, 只保留行号
    lines = [sig.split(':')[-1] for sig in patch_changes]
    # 执行测试收集覆盖
    funcs = []
    tests_list = test_preprocess.get_tests(test_dir_root, include_pattern)
    args = []
    count = 0
    for test in tests_list:
        tmp_dir_subprocess = f'{tmp_dir}_{str(count)}'
        shutil.copytree(tmp_dir, tmp_dir_subprocess)
        count += 1
        cmd = run_tests_with_coverage_cmd.format(work_dir=tmp_dir_subprocess, test_dir=test_dir_root, single_test=test, include=include, failing_output=failing_output)
        args.append((tmp_dir_subprocess, cmd, test, lines))
    with multiprocessing.Pool(processes=len(tests_list)) as pool:
        results = pool.imap_unordered(
            process_coverage_for_each_test,
            args
        )
        funcs.extend(results)
    # 删除缺陷无关的测试
    logging.info(f'deleting irrelative tests for {proj}_{id}-{test_dir}...')
    new_test_root = test_preprocess.filter_irrelative_tests(proj, id, tests_root, funcs, test_dir, include_pattern)
    return new_test_root


def process_coverage_for_each_test(args):
    work_dir, cmd, test, lines = args
    logging.info(f'running cmd {cmd}')
    result = run_cmd(work_dir, cmd.split(' '))
    coverage_file_path = f'{work_dir}/coverage.xml'
    covered = read_coverage(coverage_file_path, lines)
    if covered:
        test_name = test.split('::')[-1]
        return test_name
    return None


def read_coverage(file_path, lines):
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        for cls in root.findall(".//class"):
            cls_name = cls.get('name')
            # todo 更准确的做法还需要比较类名和函数名……
            for line in cls.findall(".//line"):
                line_number = int(line.get('number'))
                hits = int(line.get('hits'))
                if line_number in lines:
                    return hits > 0
    except Exception as e:
        logging.error(f'解析xml文件{file_path}时出现错误：{str(e)}')
    return False


def mapping_test_dirs(proj, id, test_dir):
    if not os.path.exists(util_infos_file_path):
        return test_dir
    logging.info(f'mapping test_dir for {test_dir}...')
    try:
        # 获取df，判断是否有包名变换
        # **df中的路径要和test_dir下的目录结构一致！！！***
        info_df = pd.read_csv(util_infos_file_path)
        mask = (info_df['proj'] == proj) & (info_df['id'] == int(id))
        info_df = info_df[mask]
        if info_df.empty:
            return test_dir

        # # 复制test文件到新的目录并修改目录名
        # cp_test_dir = f'{test_dir}_original'
        # if os.path.exists(cp_test_dir):
        #     return cp_test_dir
        # shutil.copytree(test_dir, cp_test_dir)
        cp_test_dir = test_dir

        path_mappings = []
        for index, row in info_df.iterrows():
            buggy_test_dir = f'{cp_test_dir}/{row['buggy']}'
            if not os.path.exists(buggy_test_dir):
                continue
            original_test_dir = f'{cp_test_dir}/{row['original']}'
            path_mappings.append({
                'buggy': row['buggy'],
                'original': row['original']
            })
            parent = os.path.dirname(original_test_dir)
            if not os.path.exists(parent):
                os.makedirs(parent)
            shutil.move(buggy_test_dir, original_test_dir)

        # 修改java类的package和import中的包名
        mapping_package_name(path_mappings, cp_test_dir)
        return cp_test_dir
    except Exception as e:
        logging.error(f'包名转换出错: {str(e)}')
        return test_dir


def mapping_package_name(path_mappings, curr_dir):
    # 1. 获取当前目录下以include结尾的文件
    # 2. 读取文件内容
    # 3. 匹配package和import开头的行
    # 4. 匹配info_df['buggy']到info_df['original'](先转换文件路径为包名)
    try:
        for root, _, files in os.walk(curr_dir):
            for file in files:
                if not re.match(include_pattern, file):
                    continue
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except Exception as e:
                    logging.error(f'file {file_path} reading error: {str(e)}')
                    continue
                find_any = [item for item in path_mappings if item['original'] in file_path]
                if len(find_any) == 0:
                    continue
                
                buggy_package = find_any[0]['buggy'].replace('/', '.').strip('.')
                original_package = find_any[0]['original'].replace('/', '.').strip('.')
                package_pattern = re.compile(
                    r'^(package|import)\s+' + 
                    re.escape(buggy_package) + 
                    r'(\..*?|;)', 
                    flags=re.MULTILINE
                )
                update_content = package_pattern.sub(
                    fr'\1 {original_package}\2', 
                    content
                )
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(update_content)
                logging.info(f'update mapping tests successfully: {buggy_package}->{original_package}')
    except Exception as e:
        logging.error(f'mapping tests file {file_path} error: {str(e)}')


def run_cmd(work_dir, cmd):
    result = subprocess.run(cmd, cwd=work_dir, capture_output=True, text=True)
    if result.returncode == 0:
        logging.info('EXECUTION SUCCESS!')
    else:
        logging.info('EXECUTION FAILED!')
    return result


def main(funcs_df, test_prefix): 
    df = pd.read_csv(bugs_info)
    proj_bugs = [item for item in df['bug_name'].tolist()]
    for proj_bug in tqdm(proj_bugs):
        proj = proj_bug.split('_')[0]
        id = proj_bug.split('_')[1]
        patch_changes = funcs_df.query(f"proj == '{proj}' and id == {id}").iloc[0]['patch_changes']
        test_dir_root = f'{tests_root}/{proj}/{id}'
        if not os.path.exists(test_dir_root):
            continue

        # 确认目录存在，不存在则checkout
        work_dir = f'{bugs_root}/{proj}/{proj}_{id}_{version}'
        sha = None
        if version == 'original':
            sha = df.set_index('bug_name')['originalCommit'].get(proj_bug)
        checkout(proj, id, work_dir, version, sha)
        
        # 创建临时工作目录
        tmp_dir = f'{tmp_dir_root}/{proj}_{id}'
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)
        shutil.copytree(work_dir, tmp_dir)

        test_dirs = [entry.name for entry in os.scandir(test_dir_root) if entry.is_dir()]
        # 对每个测试目录运行测试
        for test_dir in test_dirs:
            # logging.info(test_dir)
            run_tests(patch_changes, tmp_dir, proj, id, version, test_prefix, f'{test_dir_root}/{test_dir}')


def test_one(proj, id, test_dir, test_prefix):
    version = 'original'
    # 确认目录存在，不存在则checkout
    work_dir = f'{bugs_root}/{proj}/{proj}_{id}_{version}'
    checkout(proj, id, work_dir, version)
    # 创建临时工作目录
    tmp_dir = f'{tmp_dir_root}/{proj}_{id}'
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)
    shutil.copytree(work_dir, tmp_dir)
    # 复制测试到对应的结果目录
    test_dir_root = f'{tests_root}/{proj}/{id}'
    target_test_root = f'{result_root}/{test_prefix}/{proj}/{id}'
    shutil.copytree(test_dir_root, target_test_root, dirs_exist_ok=True)
    run_tests(tmp_dir, proj, id, version, test_prefix, f'{target_test_root}/{test_dir}')


def rerun(df, test_prefix):
    for _, row in tqdm(df.iterrows()):
        proj = row['proj']
        id = row['id']
        version = 'original'
        # 确认目录存在，不存在则checkout
        work_dir = f'{bugs_root}/{proj}/{proj}_{id}_{version}'
        test_dir_root = f'{tests_root}/{proj}/{id}'
        
        # 创建临时工作目录
        tmp_dir = f'{tmp_dir_root}/{proj}_{id}'
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)
        shutil.copytree(work_dir, tmp_dir)

        test_dirs = [entry.name for entry in os.scandir(test_dir_root) if entry.is_dir()]
        # 对每个测试目录运行测试
        for test_dir in test_dirs:
            # logging.info(test_dir)
            run_tests(tmp_dir, proj, id, version, test_prefix, f'{test_dir_root}/{test_dir}')



if __name__ == '__main__':
    for task in tasks:
        tasks.set_description('Processing for run tests for %s' % task)
        version = str(task)
        df = pd.read_csv(util_infos_file_path)
        funcs_df = test_preprocess.get_bug_relative_funcs(df)
        
        for test_prefix in test_prefixes:
            if 'evosuite' in test_prefix:
                include = '*_ESTest.java'
                include_pattern = r'.*_ESTest\.java$'
            tests_root = Constant.TESTS_ROOT[test_prefix]# 测试文件存放路径
            
            result_root = f'{result_dir_root}/{version}_result/'
            logging.info(f'running for {version}...')
            main(funcs_df, test_prefix)
            time.sleep(.1)

    # test_one('Math', '2', '2')

    # df = pd.read_csv('/mnt/Benchmark_py/tests_study/original_result/SwitchAndClean/switch_analysis.csv')
    # df = df[df['error_reason'].isna()]
    # rerun(df)
