#!/usr/bin/env python3
import os
import sys

VERBOSE = False

def read_proc(filename):
    with open(filename, encoding='ascii') as fp:
        return fp.readline().rstrip()

def cpu_list(cpu_line):
    if cpu_line.strip() == '(null)':
        return []

    cpus = []
    for part in cpu_line.split(','):
        if '-' in part:
            parts = part.split('-', 1)
            first = int(parts[0])
            last = int(parts[1])
            for cpu in range(first, last+1):
                cpus.append(cpu)
        else:
            cpus.append(int(part))
    return cpus

filename = '/sys/devices/system/cpu/isolated'
cpu_isolated = read_proc(filename)

if not cpu_isolated:
    print("ERROR: %s is empty, no CPU isolated!" % filename)
    sys.exit(1)

nohz_full = read_proc('/sys/devices/system/cpu/nohz_full')
nohz_full = set(cpu_list(nohz_full))

cpus = cpu_list(cpu_isolated)
if VERBOSE:
    print("%s isolated CPUs: %s" % (len(cpus), cpu_isolated))
    for cpu in cpus:
        governor = read_proc('/sys/devices/system/cpu/cpu%s/cpufreq/scaling_governor' % cpu)
        print("CPU #%s: scaling governor %r, no HZ full: %s"
              % (cpu, governor, cpu in nohz_full))
    print(flush=True)

args = ['/usr/bin/taskset', '-c', cpu_isolated]
args.extend(sys.argv[1:])
os.execv(args[0], args)
