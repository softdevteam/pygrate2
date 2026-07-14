import sys
import os
import subprocess
import re
import optparse

from lib2to3 import refactor
from .semrefactor import ProgramContext, SemanticRefactoringTool

def main():
    parser = optparse.OptionParser(usage="pygrate2 [options] source dest")
    parser.add_option("-r", "--run", action="store_true",
                        help="Run program with warnings. If source is a directory, it runs as a module.")

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

    input_base_dir = args[0]
    if (not input_base_dir.endswith(os.sep) and not os.path.isdir(input_base_dir)):
        input_base_dir = os.path.dirname(input_base_dir)
    input_base_dir = input_base_dir.rstrip(os.sep)

    lib2to3_fixer_names = ['lib2to3.fixes.fix_numliterals']
    fixer_names = lib2to3_fixer_names + refactor.get_fixers_from_package('pygrate2.fixes')

    program_context = ProgramContext()

    tool = SemanticRefactoringTool(
            fixers=fixer_names,
            program_context=program_context,
            options=None,
            explicit=None,
            nobackups=True,
            show_diffs=True,
            input_base_dir=input_base_dir,
            output_dir=args[1])

    if os.path.isdir(args[0]):
        tool.refactor_dir(args[0], write=True)
    else:
        tool.refactor_file(args[0], write=True)

    if not options.run:
        return

    proc_args = [sys.executable, '-3']
    if os.path.isdir(args[0]):
        proc_args.append('-m')
    proc_args.append(args[0])

    proc = subprocess.Popen(proc_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    stdoutdata, stderrdata = proc.communicate()

    print ''
    print stdoutdata

    warning_pattern = re.compile(r"(.+):(\d+): (.*)Warning: (.*)")

    for line in stderrdata.splitlines():
        m = re.match(warning_pattern, line)

        if m is not None:
            warning = m.group(1, 2, 3, 4)
            print warning
