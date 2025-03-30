import os
import sys
import subprocess
import logging

py_log_file_name = 'switch.log'

# 需要更改的目录位置
result_dir_root = '/mnt/Benchmark_py/tests_study/'# 测试结果存放路径
jar_path = '/mnt/Benchmark_py/lib/SwitchAndClean.jar'#jar包的路径

########## 以下均不要更改 ##########
result_root = f'{result_dir_root}/original_result'
py_log_file = f'{result_root}/{py_log_file_name}'
if os.path.exists(py_log_file):
      os.remove(py_log_file)
logging.basicConfig(filename=py_log_file, level=logging.INFO)
      
# default_properties = '/mnt/Benchmark_py/lib/default.properties'#  -Dexternal.properties.path={default_properties}
cmd = f'{os.getenv('JAVA_11_HOME')}/bin/java -cp '\
      + '{jarPath} '\
      'root.script.SwitchAndClean {proj} {id} {version} {workingDir} {sha}'

def run_cmd(work_dir, cmd):
      result = subprocess.run(cmd, cwd=work_dir, capture_output=True, text=True)
      if result.returncode == 0:
            logging.info('EXECUTION SUCCESS!')
      else:
            logging.info('EXECUTION FAILED!')
      return result


def run(p, i, v, w, s):
      change_cmd = cmd.format(jarPath=jar_path, proj=p, id=i, version=v, workingDir=w, sha=s)
      logging.info(change_cmd)
      work_dir = f'{result_root}/SwitchAndClean/{p}/{i}/'
      if not os.path.exists(work_dir):
            os.makedirs(work_dir)
      res = run_cmd(work_dir=work_dir, cmd=change_cmd.split(' '))
      # if res.stdout == '0\n':
      #       logging.info('changing successly.')
      # else:
      #       logging.info('error occurred!')
      return res.returncode


if __name__ == '__main__':
      argvs = sys.argv
      p = argvs[1]
      i = argvs[2]
      v = argvs[3]
      w = argvs[4]
      s = argvs[5]
      run(p, i, v, w, s)
