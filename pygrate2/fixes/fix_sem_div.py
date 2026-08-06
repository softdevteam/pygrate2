from lib2to3.fixer_util import Name, Comma, Call
from lib2to3.pygram import python_symbols
from lib2to3.pgen2 import token
from lib2to3.pytree import Node, Leaf

from .. import semfixer_base

class FixSemDiv(semfixer_base.SemanticFix):
    HELPER_FUNCTION = u'classic_div'

    def match(self, node):
        if node.type == python_symbols.term:
            for child in node.children[1::2]:
                if child.type == token.SLASH:
                    return True
        return False

    def transform(self, node, results):
        dividend_nodes = []
        term_children = iter(node.children)
        for child in term_children:
            if child.type == token.SLASH:
                dividend = Node(python_symbols.term, dividend_nodes, prefix=u'')
                divisor = term_children.next().clone()
                divisor.prefix = u' '
                dividend_nodes = [Call(Name(self.HELPER_FUNCTION), [dividend, Comma(), divisor])]
                self.wrote_helper = True
            else:
                dividend_nodes.append(child.clone())
        return Node(python_symbols.term, dividend_nodes, prefix=node.children[0].prefix)
