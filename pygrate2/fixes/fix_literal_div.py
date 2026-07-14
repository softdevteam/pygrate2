from lib2to3 import fixer_base, pytree
from lib2to3.pgen2 import token

from ..refactor_util import is_integer_literal

class FixLiteralDiv(fixer_base.BaseFix):
    # assumes FixNumliterals is run first

    PATTERN = "term< dividend=NUMBER operator='/' divisor=NUMBER >"

    def match(self, node):
        results = super(FixLiteralDiv, self).match(node)
        if not results:
            return False

        if is_integer_literal(results['dividend']) and is_integer_literal(results['divisor']):
            return results

        return False

    def transform(self, node, results):
        operator = results["operator"]
        operator.replace(pytree.Leaf(token.DOUBLESLASH, u"//", prefix=operator.prefix))
