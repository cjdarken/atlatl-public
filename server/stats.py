import numpy as np
from scipy import stats
from pathlib import Path

def compute_mean(name):
    # Load the data from the two files
    def load_data(file_path):
        with open(file_path, 'r') as file:
            data = [float(line.strip()) for line in file]
        return data
    file = name+".data"
    if not Path(file).is_file():
        return "unknown"
    data = load_data(file)
    return np.mean(data)

def compute_sem(name):
    # Load the data from the two files
    def load_data(file_path):
        with open(file_path, 'r') as file:
            data = [float(line.strip()) for line in file]
        return data
    file = name+".data"
    if not Path(file).is_file():
        return "unknown"
    data = load_data(file)
    return stats.sem(data)

def ttest(file1,file2):

    # Load the data from the two files
    def load_data(file_path):
        with open(file_path, 'r') as file:
            data = [float(line.strip()) for line in file]
        return data

    # Load data
    data1 = load_data(file1)
    data2 = load_data(file2)

    # Ensure both files have the same number of data points
    if len(data1) != len(data2):
        raise ValueError("The two files must have the same number of data points for a paired t-test.")

    # Perform the paired t-test
    t_stat, p_value = stats.ttest_rel(data1, data2)

    # Calculate means and standard errors of the mean (SEM)
    mean1 = np.mean(data1)
    mean2 = np.mean(data2)

    sem1 = stats.sem(data1)
    sem2 = stats.sem(data2)

    # Output the results
    print(f"{file1} mean {mean1}+-{sem1} {file2} {mean2}+-{sem2} p: {p_value}")
    if p_value>0.05:
        print(f'{file1} ? {file2} {p_value}')
    else:
        if mean1>mean2:
            print(f'{file1} > {file2} {p_value}')
        else:
            print(f'{file2} > {file1} {p_value}')

def ttests():
    ttest("pass-agg.data", "pass-agg-pseudo-q-fixed.data")
    ttest("pass-agg.data", "pass-agg-state-fixed.data")
    ttest("pass-agg-state-fixed.data", "pass-agg-pseudo-q-fixed.data")

    ttest("pass-agg-state-greedy.data", "pass-agg-pseudo-q-greedy.data")

    ttest("stomp-scoring-greedy.data", "stomp-pp.data")
    ttest("stomp.data", "stomp-scoring-full.data")
    ttest("pass-agg-fp.data", "pass-agg-state.data")

def means():
    def print_result(fname):
        print(f'{fname} {compute_mean(fname)}+-{compute_sem(fname)}')

    print_result('pass-agg')
    print_result('pass-agg-pseudo-q-fixed')
    print_result('pass-agg-state-fixed')
    print()
    print_result('pass-agg-pseudo-q-greedy')
    print_result('pass-agg-state-greedy')
    print()
    print_result('pass-agg-fp')
    print_result('pass-agg-state-full')
    print()
    print()
    print_result('stomp-pp')
    print_result('stomp-scoring-greedy')
    print()
    print_result('stomp')
    print_result('stomp-scoring-full')

 
means()
