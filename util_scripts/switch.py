import os
import sys
import subprocess

result_root = '/mnt/Benchmark_py/tests_study/original_result'


jar_path = '/mnt/Benchmark_py/lib/SwitchAndClean.jar'
cmd = f'{os.getenv('JAVA_11_HOME')}/bin/java -cp ' + '{jarPath}'\
      ' root.script.SwitchAndClean {proj} {id} {version} {workingDir} {sha}'

def run_cmd(work_dir, cmd):
      result = subprocess.run(cmd, cwd=work_dir, capture_output=True, text=True)
      if result.returncode == 0:
            print('EXECUTION SUCCESS!')
      else:
            print('EXECUTION FAILED!')
      return result


def run(p, i, v, w, s):
      change_cmd = cmd.format(jarPath=jar_path, proj=p, id=i, version=v, workingDir=w, sha=s)
      print(change_cmd)
      work_dir = f'{result_root}/SwitchAndClean/{p}/{i}/'
      if not os.path.exists(work_dir):
            os.makedirs(work_dir)
      res = run_cmd(work_dir=work_dir, cmd=change_cmd.split(' '))
      if res.stdout == '0\n':
            print('changing successly.')
      else:
            print('error occurred!')


if __name__ == '__main__':
      argvs = sys.argv
      p = argvs[1]
      i = argvs[2]
      v = argvs[3]
      w = argvs[4]
      s = argvs[5]
      run(p, i, v, w, s)
