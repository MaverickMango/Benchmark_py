import os, sys
from pathlib import Path
import subprocess
import shutil

defects4j_root = os.getenv('DEFECTS4J_HOME')
run_tests_cmd = '/'.join([defects4j_root, 'framework', 'bin', 'run_external_tests.pl'])
bugs_root = '/mnt/experiments/bugs'
tests_root = '/mnt/experiments/APCA21/RGT/2019/evosuite'
result_root = '/mnt/Benchmark_py/tests_study/buggy_result/'
cwd = os.getcwd()


def checkout(proj, id, work_dir):
    if os.path.exists(work_dir):
        return
    print(f'checking out {proj}_{id}...')
    checkout_cmd = f'defects4j checkout -p {proj} -v {id}b -w {work_dir}'
    checkout_cmd = checkout_cmd.split(' ')
    run_cmd(cwd, checkout_cmd)


def run_tests(word_dir, proj, id, version, test_prefix, test_dir, log_file, failing_output):
    tmp_dir = f'/mnt/tmp/{proj}_{id}'
    if not os.path.exists(tmp_dir):
        shutil.copytree(word_dir, tmp_dir)
    test_dir = f'{tests_root}/{proj}/{id}/{test_dir}'
    log_file = f'{result_root}/{test_prefix}/{proj}/{id}/{log_file}'
    if os.path.exists(log_file):
        os.remove(log_file)
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    failing_output = f'{result_root}/{test_prefix}/{proj}/{id}/{failing_output}'
    if os.path.exists(failing_output):
        os.remove(failing_output)
    
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
    
    cmd = f'{run_tests_cmd} -p {proj} -v {id}{version} -w {tmp_dir} -t {test_dir} -o {failing_output}'
    print(f'running tests for {proj}_{id}_buggy...')
    cmd = cmd.split(' ')
    result = run_cmd(word_dir, cmd)
    
    if result.stdout == '0\n':
        with open(log_file, 'x') as f:
            f.write(result.stdout)
    else:
        print('tests running failied.')
        with open(log_file, 'x') as f:
            f.write(result.stderr)
        


def run_cmd(work_dir, cmd):
    result = subprocess.run(cmd, cwd=work_dir, capture_output=True, text=True)
    if result.returncode == 0:
        print('EXECUTION SUCCESS!')
    else:
        print('EXECUTION FAILED!')
    return result


def run(bugs_root, tests_root):
    print()


if __name__ == '__main__':
    proj = 'Lang'
    id = '51'
    word_dir = f'{bugs_root}/{proj}/{proj}_{id}_buggy'
    test_dir = f'0'
    log_file = 'logfile.txt'
    failing_output = 'failing_tests'
    run_tests(word_dir, proj, id, 'buggy', 'evosuite2019', test_dir, log_file, failing_output)
