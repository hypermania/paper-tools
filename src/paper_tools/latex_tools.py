import pylatexenc.latexwalker as latexwalker
import pylatexenc.latexnodes as latexnodes
from pylatexenc.latexwalker import LatexWalker, LatexCommentNode
from pylatexenc.latex2text import LatexNodes2Text

from texoutparse import LatexLogParser
import pipe
import re

def extract_latex(text:str):
    strip_regex = r"\`\`\`latex(.+)\`\`\`"
    matches = re.findall(strip_regex, text, re.DOTALL)
    if len(matches) > 0:
        return matches[0]
    else:
        return text

def extract_head_lines(text:str, lines=10):
    return "\n".join(text.split('\n')[:lines])


def is_latex_well_formed(tex_content):
    # Parse the LaTeX content and collect errors
    walker = LatexWalker(tex_content, tolerant_parsing=False)
    try:
        nodelist, parsing_state_delta = walker.parse_content(
            latexnodes.parsers.LatexGeneralNodesParser()
        )
        is_well_formed = True
    except:
        is_well_formed = False
        
    return is_well_formed


class MyVisitor(latexnodes.nodes.LatexNodesVisitor):
    def __init__(self):
        self.result = []
    def visit_macro_node(self, node, **kwargs):
        if node.macroname == 'section':
            self.result.append(node)

def extract_sections(paper: str):
    my_latex_walker = latexwalker.LatexWalker(paper)
    nodelist, parsing_state_delta = my_latex_walker.parse_content(
        latexnodes.parsers.LatexGeneralNodesParser()
        #    parsing_state=parsing_state
    )
    npos = nodelist.pos
    nlen = nodelist.len # or nodelist.pos_end - nodelist.pos
    
    visitor = MyVisitor()
    visitor.start(nodelist)
    
    section_pos = list(visitor.result | pipe.map(lambda node: node.pos))
    needed_sections = [(section_pos[i], section_pos[i+1]) for i in range(len(section_pos)-1)]
    section_text = [paper[s[0]:s[1]] for s in needed_sections]
    
    return section_text
