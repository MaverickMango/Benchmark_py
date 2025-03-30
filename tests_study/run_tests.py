import os, sys
from pathlib import Path
import subprocess
import shutil
import pandas as pd
from tqdm import *
import time

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from util_scripts import switch

# 默认参数
version = 'buggy' #执行测试的缺陷版本
test_prefix = 'evosuite2019' #跟结果文件存放的路径名以及inclue的Test类文件名有关

# 可以不更改的默认值
include = '*.java' #如果只执行目录下指定名字的测试类则更改该参数
if 'evosuite' in test_prefix:
    include = '*_ESTest.java'
log_file_name = 'logfile.txt'
failing_output_name = 'failing_tests'

# 需要更改的目录位置
tmp_dir_root = '/tmp' # 临时工作文件夹的根目录
bugs_root = '/mnt/experiments/bugs' # 下载的所有bug的根目录 缺陷目录为f'{bugs_root}/{proj}/{proj}_{id}_{version}'
tests_root = '/mnt/experiments/APCA21/RGT/2019/evosuite'# 测试文件存放路径
result_dir_root = '/mnt/Benchmark_py/tests_study/'# 测试结果存放路径
bugs_info = '/mnt/Benchmark_py/bugs_inputs.csv' #存放需要测试的缺陷信息

########## 以下均不要更改 ##########
result_root = f'{result_dir_root}/{version}_result'
# defects4j_root = os.getenv('DEFECTS4J_HOME')
# run_tests_cmd = '/'.join([defects4j_root, 'framework', 'bin', 'run_external_tests.pl'])
run_tests_cmd = 'defects4j external.test'
cwd = os.getcwd()


def checkout(proj, id, work_dir, version):
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
    print(f'checking out {proj}_{id}{version}...')
    checkout_cmd = f'defects4j checkout -p {proj} -v {id}{version} -w {work_dir}'
    checkout_cmd = checkout_cmd.split(' ')
    run_cmd(cwd, checkout_cmd)


def run_tests(tmp_dir, proj, id, version, test_prefix, test_dir):

    log_file = f'{result_root}/{test_prefix}/{proj}/{id}/{test_dir}/{log_file_name}'
    if os.path.exists(log_file):
        os.remove(log_file)
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    # print(log_file)
    failing_output = f'{result_root}/{test_prefix}/{proj}/{id}/{test_dir}/{failing_output_name}'
    if os.path.exists(failing_output):
        os.remove(failing_output)
    last_failing_test = f'{tmp_dir}/failing-tests.txt'
    if os.path.exists(last_failing_test):
        os.remove(last_failing_test)
    
    test_dir = f'{tests_root}/{proj}/{id}/{test_dir}'

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
    
    print(f'running tests for {proj}_{id}{version}...')
    cmd = f'{run_tests_cmd} -p {proj} -v {id}{version} -w {tmp_dir} -t {test_dir} -i {include} -o {failing_output}' # 加了-o之后没有junit执行的报错信息
    print(cmd)
    cmd = cmd.split(' ')
    result = run_cmd(tmp_dir, cmd)
    if os.path.exists(last_failing_test):
        shutil.copyfile(last_failing_test, failing_output)

    # print(result.stderr + result.stdout)
    if result.stdout == '0\n':
        print('tests running success.')
    else:
        print('tests running failied.')
    with open(log_file, 'x') as f:
        f.write(result.stderr + result.stdout)
        

def run_cmd(work_dir, cmd):
    result = subprocess.run(cmd, cwd=work_dir, capture_output=True, text=True)
    if result.returncode == 0:
        print('EXECUTION SUCCESS!')
    else:
        print('EXECUTION FAILED!')
    return result


def main(): 
    df = pd.read_csv(bugs_info)
    proj_bugs = [item for item in df['bug_name'].tolist()]
    for proj_bug in tqdm(proj_bugs):
        proj = proj_bug.split('_')[0]
        id = proj_bug.split('_')[1]
        test_dir_root = f'{tests_root}/{proj}/{id}'
        if not os.path.exists(test_dir_root):
            continue

        # 确认目录存在，不存在则checkout
        work_dir = f'{bugs_root}/{proj}/{proj}_{id}_{version}'
        checkout(proj, id, work_dir, version)
        if version == 'original':
            sha = df.set_index('bug_name')['originalCommit'].get(proj_bug)
            change_res = switch.run(proj, id, version, work_dir, sha)
            if change_res != '0':
                print(f'Error occurred when switch {proj}_{id}_{version}, skip this defect.')
                continue
        
        # 创建临时工作目录
        tmp_dir = f'{tmp_dir_root}/{proj}_{id}'
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)
        shutil.copytree(work_dir, tmp_dir)

        test_dirs = [entry.name for entry in os.scandir(test_dir_root) if entry.is_dir()]
        # 对每个测试目录运行测试
        for test_dir in test_dirs:
            # print(test_dir)
            run_tests(tmp_dir, proj, id, version, test_prefix, test_dir)


def test_one(proj, id, test_dir):
    version = 'buggy'
    # 确认目录存在，不存在则checkout
    work_dir = f'{bugs_root}/{proj}/{proj}_{id}_{version}'
    checkout(proj, id, work_dir, version)
    # 创建临时工作目录
    tmp_dir = f'{tmp_dir_root}/{proj}_{id}'
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)
    shutil.copytree(work_dir, tmp_dir)
    run_tests(tmp_dir, proj, id, version, test_prefix, test_dir)


if __name__ == '__main__':
    tasks = tqdm(['fixing', 'original', 'buggy'])
    for task in tasks:
        tasks.set_description('Processing for run tests for %s' % task)
        version = str(task)
        result_root = f'{result_dir_root}/{version}_result/{test_prefix}'
        main()
        time.sleep(.1)
    # test_one('Lang', '26', '0')

