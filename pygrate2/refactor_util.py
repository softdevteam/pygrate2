import re
import ast

from lib2to3.pytree import Leaf

# assumes FixNumliterals was run
def is_integer_literal(node):
    if isinstance(node, Leaf):
        return re.match('(?:[1-9][0-9]*|0(?:[oO][0-7]+|[xX][0-9a-fA-F]+|[bB][01]+)?)$', node.value) is not None
    return False
