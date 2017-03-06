#!/usr/bin/env python3
"""
Configure a Linux system with isolated CPUs to run benchmarks, see:
http://haypo-notes.readthedocs.org/microbenchmark.html
"""

import os
import sys

# used to debug
WRITE = True

IRQ_PATH = "/proc/irq/"
IRQ_DEFAULT_SMP_AFFINITY = "/proc/irq/default_smp_affinity"
IRQ_SMP_AFFINITY = "/proc/irq/%s/smp_affinity"
ASLR_FILENAME = "/proc/sys/kernel/randomize_va_space"
ISOLATED_FILENAME = '/sys/devices/system/cpu/isolated'
DRIVER_FILENAME = "/sys/devices/system/cpu/cpu%s/cpufreq/scaling_driver"
GOVERNOR_FILENAME = "/sys/devices/system/cpu/cpu%s/cpufreq/scaling_governor"


def read_proc(filename):
    with open(filename, encoding='ascii') as fp:
        return fp.readline().rstrip()


def write_proc(errors, filename, line):
    if not WRITE:
        errors.append("Write disabled manually (%s)" % filename)
        return

    try:
        with open(filename, "w", encoding='ascii') as fp:
            fp.write(line + "\n")
            fp.flush()

        # FIXME: on error, only log an error if the value changes
    except PermissionError:
        errors.append("Not allowed to write into %s" % filename)
    except OSError as exc:
        errors.append("Failed to write %r into %s: %s"
                      % (line, filename, exc))


def cpu_list(cpu_line):
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


def main():
    errors = []

    cpu_count = os.cpu_count()
    if not cpu_count:
        print("ERROR: failed to get the CPU count")
        sys.exit(1)
    print("CPU count: %s" % cpu_count)
    all_cpus = tuple(range(cpu_count))

    cpu_isolated = read_proc(ISOLATED_FILENAME)
    if not cpu_isolated:
        print("ERROR: %s is empty, no CPU isolated!" % ISOLATED_FILENAME)
        sys.exit(1)
    print("Isolated CPUs: %s" % cpu_isolated)
    cpus = cpu_list(cpu_isolated)
    cpu_set = set(cpus)

    # Create the mask
    mask = 0
    for cpu in range(cpu_count):
        if cpu not in cpu_set:
            mask |= 1 << cpu
    mask = "%x" % mask
    print("Mask: %s" % mask)

    # Scaling governor
    intel_pstate = (read_proc(DRIVER_FILENAME % 0) == 'intel_pstate')

    if intel_pstate:
        governor = "performance"
        # Documentation of the Intel P-state driver:
        # "Since each CPU has a
        #  cpufreq sysfs, it is possible to set a scaling governor to each CPU.
        #  But this is not possible with Intel P-States, as there is one common
        #  policy for all CPUs."
        #
        # So set the same governor on *all* CPUs
        for cpu in all_cpus:
            filename = GOVERNOR_FILENAME % cpu
            write_proc(errors, filename, governor)
    else:
        governor = "userspace"
        for cpu in cpus:
            filename = GOVERNOR_FILENAME % cpu
            write_proc(errors, filename, governor)
    for cpu in range(cpu_count):
        governor = read_proc(GOVERNOR_FILENAME % cpu)
        driver = read_proc(DRIVER_FILENAME % cpu)
        print("CPU #%s: scaling governor: %s, driver: %s"
              % (cpu, governor, driver))

    if not intel_pstate:
        for cpu in cpus:
            freq = read_proc("/sys/devices/system/cpu/cpu%s/cpufreq/scaling_max_freq" % cpu)
            write_proc(errors, "/sys/devices/system/cpu/cpu%s/cpufreq/scaling_setspeed" % cpu, freq)

    for cpu in range(cpu_count):
        try:
            freq = read_proc("/sys/devices/system/cpu/cpu%s/cpufreq/cpuinfo_cur_freq" % cpu)
        except PermissionError:
            # need root
            pass
        else:
            print("CPU #%s frequency: %s"% (cpu, freq))

    if intel_pstate:
        # Disable Turbo Mode
        write_proc(errors, '/sys/devices/system/cpu/intel_pstate/no_turbo', '1\n')

        turbo = (read_proc('/sys/devices/system/cpu/intel_pstate/no_turbo') != '1')
        print("intel_pstate Turbo Mode: %s" % turbo)

    # ASLR
    #write_proc(errors, ASLR_FILENAME, "0")
    line = read_proc(ASLR_FILENAME)
    print("Address space layout randomization (ASLR) enabled: %s"
          % (line != "0"))

    # Default IRQ affinity
    filename = IRQ_DEFAULT_SMP_AFFINITY
    write_proc(errors, filename, mask)
    line = read_proc(filename)
    print("Default IRQ affnitiy: %s" % line)

    # IRQ affinity
    irqs = [int(filename) for filename in os.listdir(IRQ_PATH) if filename.isdigit()]
    for irq in irqs:
        filename = IRQ_SMP_AFFINITY % irq
        write_proc(errors, filename, mask)

        line = read_proc(filename)
        print("IRQ #%s SMP affinity: %s" % (irq, line))

    if errors:
        for index, error in enumerate(errors):
            if index >= 3:
                print("... %s more errors ..."
                      % (len(errors) - index))
                break
            print("ERROR: %s" % error)
        sys.exit(1)


if __name__ == "__main__":
    main()
