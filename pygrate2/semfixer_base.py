from lib2to3.fixer_base import BaseFix

class SemanticFix(BaseFix):
    HELPER_FUNCTION = None

    def __init__(self, options, log, program_context=None):
        super(SemanticFix, self).__init__(options, log)
        self._program_context = program_context
        self.wrote_helper = False # whether the last call to transform refactored using HELPER_FUNCTION
