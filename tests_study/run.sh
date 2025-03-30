#!/bin/bash

run_tests="/mnt/Benchmark_py/tests_study/run_tests.py"
tests_analysis="/mnt/Benchmark_py/tests_study/test_results_analysis.py"
results_display="/mnt/Benchmark_py/tests_study/test_result_display.py"

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

if [ ! -f "$results_display" ]; then
    echo "文件 $results_display 不存在。"
    exit 1
fi
python3 "$results_display"