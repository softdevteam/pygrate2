import operator

from lib2to3.main import StdoutRefactoringTool
from .semfixer_base import SemanticFix

class ProgramContext(object):
    # example of a method that would read the source to find the possible types of a variable
    def get_possible_types(self, variable):
        pass

class SemanticRefactoringTool(StdoutRefactoringTool):
    def __init__(self, fixers, program_context, options, explicit, nobackups, show_diffs,
                 input_base_dir='', output_dir='', append_suffix=''):
        self._program_context = program_context
        super(SemanticRefactoringTool, self).__init__(fixers, options, explicit, nobackups, show_diffs,
                                                        input_base_dir, output_dir, append_suffix)

    def get_fixers(self):
        """Inspects the options to load the requested patterns and handlers.

        Returns:
          (pre_order, post_order), where pre_order is the list of fixers that
          want a pre-order AST traversal, and post_order is the list that want
          post-order traversal.
        """
        pre_order_fixers = []
        post_order_fixers = []
        for fix_mod_path in self.fixers:
            mod = __import__(fix_mod_path, {}, {}, ["*"])
            fix_name = fix_mod_path.rsplit(".", 1)[-1]
            if fix_name.startswith(self.FILE_PREFIX):
                fix_name = fix_name[len(self.FILE_PREFIX):]
            parts = fix_name.split("_")
            class_name = self.CLASS_PREFIX + "".join([p.title() for p in parts])
            try:
                fix_class = getattr(mod, class_name)
            except AttributeError:
                raise FixerError("Can't find %s.%s" % (fix_name, class_name))
            if issubclass(fix_class, SemanticFix):
                fixer = fix_class(self.options, self.fixer_log, self._program_context)
            else:
                fixer = fix_class(self.options, self.fixer_log)
            if fixer.explicit and self.explicit is not True and \
                    fix_mod_path not in self.explicit:
                self.log_message("Skipping optional fixer: %s", fix_name)
                continue

            self.log_debug("Adding transformation: %s", fix_name)
            if fixer.order == "pre":
                pre_order_fixers.append(fixer)
            elif fixer.order == "post":
                post_order_fixers.append(fixer)
            else:
                raise FixerError("Illegal fixer order: %r" % fixer.order)

        key_func = operator.attrgetter("run_order")
        pre_order_fixers.sort(key=key_func)
        post_order_fixers.sort(key=key_func)
        return (pre_order_fixers, post_order_fixers)
