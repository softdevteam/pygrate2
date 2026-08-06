import sys
import os
import subprocess
import re
import optparse

from lib2to3 import refactor
from .interactiverefactor import InteractiveRefactoringTool
from .warninginfo import WarningInfo

def main():
    parser = optparse.OptionParser(usage="pygrate2 [options] source dest")
    parser.add_option("-a", "--argv",
                        help="File that contains arguments for the program. The program is run for each line.")

    options, args = parser.parse_args()

    if len(args) == 0:
        parser.print_help()
        return
    if len(args) == 1:
        print 'Missing dest argument'
        return
    if len(args) > 2:
        print 'Too many arguments'
        return
    if not os.path.exists(args[0]):
        print 'Source path does not exist'
        return
    if options.argv and os.path.exists(options.argv):
        print 'argv path does not exist'
        return
    
    source_path = os.path.abspath(args[0])
    dest_path = os.path.abspath(args[1])

    input_base_dir = source_path
    if (not input_base_dir.endswith(os.sep) and not os.path.isdir(input_base_dir)):
        input_base_dir = os.path.dirname(input_base_dir)
    input_base_dir = input_base_dir.rstrip(os.sep)

    warnings = set()
    if not options.argv:
        warnings = run_program(source_path)
    else:
        with open(options.argv, 'r') as f:
            for line in file:
                prog_warnings = run_program(source_path, line.split())
                warnings |= prog_warnings

    warning_fixers = {'classic int division': 'fix_sem_div'}
    generate_fixer_paths(warning_fixers)

    tool = InteractiveRefactoringTool(
            warning_fixers=warning_fixers,
            options=None,
            explicit=None,
            nobackups=True,
            show_diffs=True,
            input_base_dir=input_base_dir,
            output_dir=dest_path)

    if os.path.isdir(source_path):
        tool.refactor_dir(source_path, warnings=warnings, write=True)
    else:
        tool.refactor_file(source_path, warnings=warnings, write=True)

def run_program(source, args=None):
    proc_args = [sys.executable, '-3']
    env = os.environ.copy()
    source_arg = source
    if os.path.isdir(source):
        proc_args.append('-m')
        env['PYTHONPATH'] = os.path.dirname(source.rstrip(os.sep))
        source_arg = os.path.basename(source.rstrip(os.sep))
    proc_args.append(source_arg)
    if args:
        proc_args += args

    proc = subprocess.Popen(proc_args, stderr=subprocess.PIPE, env=env)
    stdoutdata, stderrdata = proc.communicate()

    warning_pattern = re.compile(r"(.+):(\d+): (.*)Warning: (.*)")

    warnings = set()
    for line in stderrdata.splitlines():
        m = re.match(warning_pattern, line)

        if m is not None:
            warning = WarningInfo(m.group(1), int(m.group(2)), m.group(3), m.group(4))
            warnings.add(warning)

    return warnings

def generate_fixer_paths(warning_fixers):
    for warning, fixer_name in warning_fixers.iteritems():
        warning_fixers[warning] = 'pygrate2.fixes.' + fixer_name
