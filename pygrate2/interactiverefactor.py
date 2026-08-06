import os
import operator
from itertools import chain
import inspect

from lib2to3.main import StdoutRefactoringTool
from .semfixer_base import SemanticFix

class InteractiveRefactoringTool(StdoutRefactoringTool):
    def __init__(self, warning_fixers, options, explicit, nobackups, show_diffs,
                 input_base_dir='', output_dir='', append_suffix=''):
        self._warning_fixers = dict(warning_fixers)
        self._warnings = None
        self._skipped = []
        self._helper_functions = set()
        self._dir_name = None
        self._handled_warnings = set()
        
        super(InteractiveRefactoringTool, self).__init__(self._warning_fixers.values(), options, explicit, nobackups, show_diffs,
                                                        input_base_dir, output_dir, append_suffix)
        self.write_unchanged_files = True

    def get_fixers(self):
        """Inspects the options to load the requested patterns and handlers.

        Returns:
          (pre_order, post_order), where pre_order is the list of fixers that
          want a pre-order AST traversal, and post_order is the list that want
          post-order traversal.
        """
        pre_order_fixers = []
        post_order_fixers = []
        for warning_msg, fix_mod_path in self._warning_fixers.iteritems():
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
                fixer = fix_class(self.options, self.fixer_log, None)
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
            self._warning_fixers[warning_msg] = fixer

        key_func = operator.attrgetter("run_order")
        pre_order_fixers.sort(key=key_func)
        post_order_fixers.sort(key=key_func)
        return (pre_order_fixers, post_order_fixers)

    def refactor_dir(self, dir_name, write=False, doctests_only=False, warnings=None):
        self._warnings = warnings
        self._dir_name = dir_name
        super(InteractiveRefactoringTool, self).refactor_dir(dir_name, write=write, doctests_only=doctests_only)
        if self._helper_functions:
            with open(os.path.join(self._output_dir, 'pygrate_helpers.py'), 'w') as f:
                f.write(create_helpers(self._helper_functions))
        if self._skipped:
            print 'Skipped warnings:'
            for warning in self._skipped:
                print warning
        self._warnings = None
        self._skipped = []
        self._helper_functions = set()
        self._dir_name = None
    
    def refactor_file(self, filename, write=False, doctests_only=False, warnings=None):
        if warnings:
            self._warnings = warnings
        super(InteractiveRefactoringTool, self).refactor_file(filename, write=write, doctests_only=doctests_only)
        if self._dir_name is None:
            self._skipped = []

    def refactor_tree(self, tree, name):
        """Refactors a parse tree (modifying the tree in place).

        For compatible patterns the bottom matcher module is
        used. Otherwise the tree is traversed node-to-node for
        matches.

        Args:
            tree: a pytree.Node instance representing the root of the tree
                  to be refactored.
            name: a human-readable name for this tree.

        Returns:
            True if the tree was modified, False otherwise.
        """
        helper_functions = set()

        for fixer in chain(self.pre_order, self.post_order):
            fixer.start_tree(tree, name)

        #use traditional matching for the incompatible fixers
        pre_pair = self._traverse_by(self.bmi_pre_order_heads, tree.pre_order())
        post_pair = self._traverse_by(self.bmi_post_order_heads, tree.post_order())

        helper_functions |= pre_pair[0]
        helper_functions |= post_pair[0]

        self._skipped += pre_pair[1]
        self._skipped += post_pair[1]

        # obtain a set of candidate nodes
        match_set = self.BM.run(tree.leaves())

        while any(match_set.values()):
            for fixer in self.BM.fixers:
                if fixer in match_set and match_set[fixer]:
                    #sort by depth; apply fixers from bottom(of the AST) to top
                    match_set[fixer].sort(key=pytree.Base.depth, reverse=True)

                    if fixer.keep_line_order:
                        #some fixers(eg fix_imports) must be applied
                        #with the original file's line order
                        match_set[fixer].sort(key=pytree.Base.get_lineno)

                    for node in list(match_set[fixer]):
                        if node in match_set[fixer]:
                            match_set[fixer].remove(node)

                        try:
                            find_root(node)
                        except ValueError:
                            # this node has been cut off from a
                            # previous transformation ; skip
                            continue

                        if node.fixers_applied and fixer in node.fixers_applied:
                            # do not apply the same fixer again
                            continue

                        results = fixer.match(node)

                        if results:
                            new = fixer.transform(node, results)
                            if new is not None:
                                node.replace(new)
                                #new.fixers_applied.append(fixer)
                                for node in new.post_order():
                                    # do not apply the fixer again to
                                    # this or any subnode
                                    if not node.fixers_applied:
                                        node.fixers_applied = []
                                    node.fixers_applied.append(fixer)

                                # update the original match set for
                                # the added code
                                new_matches = self.BM.run(new.leaves())
                                for fxr in new_matches:
                                    if not fxr in match_set:
                                        match_set[fxr]=[]

                                    match_set[fxr].extend(new_matches[fxr])

        for fixer in chain(self.pre_order, self.post_order):
            fixer.finish_tree(tree, name)

        if self._dir_name is None:
            if helper_functions:
                self.insert_helper_defs(tree, helper_functions)
            if self._skipped:
                print 'Skipped warnings:'
                for warning in self._skipped:
                    print warning
            self._warnings = None
            self._skipped = []
            self._helper_functions = set()
        elif helper_functions:
            self.insert_helper_import(tree, helper_functions)
            self._helper_functions |= helper_functions
        return tree.was_changed

    def _traverse_by(self, fixers, traversal):
        """Traverse an AST, applying a set of fixers to each node.

        This is a helper method for refactor_tree().

        Args:
            fixers: a list of fixer instances.
            traversal: a generator that yields AST nodes.

        Returns:
            Pair of helper functions used and skipped warnings
        """
        helper_functions = set()
        skipped = []
        if not fixers:
            return (helper_functions, skipped)
        for node in traversal:
            for warning in self._warnings:
                if warning in self._handled_warnings or node.get_lineno() != warning.lineno:
                    continue
                try:
                    fixer = self._warning_fixers[warning.msg]
                    if fixer not in fixers[node.type]:
                        continue
                except:
                    print 'No fixer for warning: {}\n'.format(warning)
                    self._handled_warnings.add(warning)
                    continue
                results = fixer.match(node)
                if results:
                    potential = node.clone()
                    new = fixer.transform(potential, results)
                    # for when the fixer replaces and returns nothing
                    if new is None:
                        new = potential
                    print '{}:{}: {}'.format(warning.filename, warning.lineno, warning.msg)
                    print 'Could safely refactor:'

                    try:
                        if self.output_lock is not None:
                            with self.output_lock:
                                print_diff(unicode(node), unicode(new))
                                sys.stdout.flush()
                        else:
                            print_diff(unicode(node), unicode(new))
                    except UnicodeEncodeError:
                        warn("couldn't encode %s's diff for your terminal" %
                            (name,))
                        return

                    print 'Apply refactoring? [y/n]'
                    while True:
                        answer = raw_input('> ')
                        if answer == 'y':
                            node.replace(new)
                            node = new
                            if fixer.wrote_helper:
                                helper_functions.add(fixer.HELPER_FUNCTION)
                        elif answer == 'n':
                            skipped.append(warning)
                        else:
                            print 'Unknown command. Apply refactoring? [y/n]'
                            continue
                        break
                    self._handled_warnings.add(warning)
        return (helper_functions, skipped)
    
    def insert_helper_defs(self, tree, helper_functions):
        helper_tree = self.driver.parse_string(create_helpers(helper_functions))
        helper_tree.children[0].prefix = u'\n'
        for child in helper_tree.children[:-1]:
            tree.insert_child(-1, child)
        

    def insert_helper_import(self, tree, helper_functions):
        import_string = 'from {}.pygrate_helpers import '.format(os.path.basename(self._dir_name))
        helper_iter = iter(helper_functions)
        import_string += helper_iter.next()
        for helper in helper_iter:
            import_string += ', {}'.format(helper)
        import_stmt_tree = self.driver.parse_string('{}\n'.format(import_string))
        tree.insert_child(0, import_stmt_tree.children[0])

def create_helpers(helper_functions):
    string = u''
    mod = __import__('pygrate2.pygrate_helpers', {}, {}, list(helper_functions))
    for helper in helper_functions:
        string += inspect.getsource(getattr(mod, helper)) + '\n'
    return string

def print_diff(old, new):
    for line in old.splitlines():
        print '- {}'.format(line)
    for line in new.splitlines():
        print '+ {}'.format(line)
