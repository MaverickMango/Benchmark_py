#!/bin/bash

run_tests="/mnt/Benchmark_py/tests_study/run_tests.py"
tests_analysis="/mnt/Benchmark_py/tests_study/test_resuslts_analysis.py"

if [ ! -f "$run_tests" ]; then
    echo "文件 $run_tests 不存在。"
    exit 1
fi
python3 "$run_tests"

if [ ! -f "$tests_analysis" ]; then
    echo "文件 $tests_analysis 不存在。"
    exit 1
fi
python3 "$tests_analysis"
