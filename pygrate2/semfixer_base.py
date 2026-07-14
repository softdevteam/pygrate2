from lib2to3.fixer_base import BaseFix

class SemanticFix(BaseFix):
    def __init__(self, options, log, program_context):
        super(SemanticFix, self).__init__(options, log)
        self._program_context = program_context
