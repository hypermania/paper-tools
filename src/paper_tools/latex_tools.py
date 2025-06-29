import pylatexenc.latexwalker as latexwalker
import pylatexenc.latexnodes as latexnodes
from pylatexenc.latexwalker import LatexWalker, LatexCommentNode
from pylatexenc.latex2text import LatexNodes2Text

# from texoutparse import LatexLogParser
import pipe
import re

# TODO
# unified interface for extracting paragraphs, sections, headlines, removing comments, removing cites, finding cites, test well-formed-ness

def filter_empty(texts:list[str]):
    re_is_empty = re.compile(r"[\n\s]*", re.DOTALL)
    result = list(texts | pipe.filter(lambda t: re_is_empty.fullmatch(t) == None))
    return result
    
def split_to_paragraphs(text:str):
    return filter_empty(text.split('\n\n'))

def extract_latex(text:str):
    strip_regex = r"\`\`\`latex(.+)\`\`\`"
    matches = re.findall(strip_regex, text, re.DOTALL)
    if len(matches) > 0:
        return matches[0]
    else:
        return text

def extract_head_lines(text:str, lines=10):
    return "\n".join(text.split('\n')[:lines])

def complement_pairs(pairs:list[tuple[int, int]], final:int) -> list[tuple[int, int]]:
    """Helper function to take the complement of a collection of intervals.

    Given a collection of sub-intervals of the full interval [0, final),
    return the sub-intervals corresponding to the complement.
    For example, given sub-intervals [0,2) and [4,6) of [0, 10), return the intervals [2,4), [6,10).
    All intervals are specified by tuples (start_index, end_index).
    """
    complement = []
    cursor = 0
    for i in range(0, len(pairs)):
        complement.append((cursor, pairs[i][0]))
        cursor = pairs[i][1]
    complement.append((cursor, final))
    return complement


class NontextVisitor(latexnodes.nodes.LatexNodesVisitor):
    def __init__(self):
        self.result = []
    def visit_macro_node(self, node, **kwargs):
        nontext_macros = {'documentclass', 'usepackage', 'section', 'subsection', 'newcommand', 'def', 'author', 'date', 'bibliography', 'maketitle', 'document', 'newtheorem'}
        if node.macroname in nontext_macros:
            self.result.append(node)
    def visit_comment_node(self, node, **kwargs):
        self.result.append(node)

class CommentVisitor(latexnodes.nodes.LatexNodesVisitor):
    def __init__(self):
        self.result = []
    def visit_comment_node(self, node, **kwargs):
        self.result.append(node)

class SectionVisitor(latexnodes.nodes.LatexNodesVisitor):
    def __init__(self):
        self.result = []
    def visit_macro_node(self, node, **kwargs):
        if node.macroname == 'section':
            self.result.append(node)
        
class LatexSnippet:
    """Handles a piece of LaTeX code. Could be an entire tex file or just a snippet."""
    
    def __init__(self, text:str):
        """Initialize the class with the LaTeX code input."""
        self.text = text
        self.walker = latexwalker.LatexWalker(text)
        
    def is_well_formed(self):
        """Return true if the snippet is well-formed LaTeX code."""
        try:
            nodelist, parsing_state_delta = self.walker.parse_content(
                latexnodes.parsers.LatexGeneralNodesParser()
            )
            is_well_formed = True
        except:
            is_well_formed = False
        
        return is_well_formed

    def get_intervals(self, visitor_class, reverse=False):
        """Extract start and end positions of the LaTeX code given a visitor class.

        Extract start and end positions of the LaTeX code that is visited by visitor.
        Complement the intervals if reverse is set to True.
        """
        nodelist, parsing_state_delta = self.walker.parse_content(
            latexnodes.parsers.LatexGeneralNodesParser()
        )

        npos = nodelist.pos
        nlen = nodelist.len
        # print("npos = {}, nlen = {}, len(text) = {}".format(npos, nlen, len(self.text)))

        visitor = visitor_class()
        visitor.start(nodelist)

        result = list(visitor.result | pipe.select(lambda n: (n.pos, n.pos_end)))
        if reverse:
            result = complement_pairs(result, len(self.text))
        
        return result

    def get_subtext(self, intervals:list[tuple[int,int]]):
        """Extract text corresponding to the intervals (start and end positions)."""
        return "".join([self.walker.s[p[0]:p[1]] for p in intervals])

    def get_split_subtext(self, intervals:list[tuple[int,int]]):
        """Extract text corresponding to the intervals (start and end positions)."""
        return [self.walker.s[p[0]:p[1]] for p in intervals]

    def comments_removed(self):
        intervals = self.get_intervals(CommentVisitor, reverse=True)
        return self.get_subtext(intervals)

    def nontext_removed(self):
        try:
            intervals = self.get_intervals(NontextVisitor, reverse=True)
        except:
            print(self.walker.s)
            print("IS TRUE: {}".format(self.walker.s == None))
        return self.get_subtext(intervals)

    def get_paragraphs(self):
        """Extract the paragraphs of a full tex file."""
        cleaned = self.comments_removed()
        paragraphs = split_to_paragraphs(cleaned)
        #raw_paragraphs = list(paragraphs | pipe.select(lambda p: LatexSnippet(p).nontext_removed()))
        return filter_empty(paragraphs)

    def get_sections(self):
        nodelist, parsing_state_delta = self.walker.parse_content(
            latexnodes.parsers.LatexGeneralNodesParser()
        )
        npos = nodelist.pos
        nlen = nodelist.len
        
        visitor = SectionVisitor()
        visitor.start(nodelist)
    
        section_pos = list(visitor.result | pipe.select(lambda node: node.pos))
        needed_sections = [(section_pos[i], section_pos[i+1]) for i in range(len(section_pos)-1)]
        sections = [self.walker.s[p[0]:p[1]] for p in needed_sections]
    
        return sections

    def get_maintext(self):
        """Extract the main text of a full tex file."""
        cleaned = self.comments_removed()
        cleaned_snippet = LatexSnippet(cleaned)
        nontext = cleaned_snippet.nontext_removed()
        return nontext

def is_latex_well_formed(text:str):
    return LatexSnippet(text).is_well_formed()

def extract_sections(paper: str):
    return LatexSnippet(text).get_sections()
    
    
__all__ = ["LatexSnippet", "NontextVisitor", "CommentVisitor", "SectionVisitor", "filter_empty", "split_to_paragraphs", "is_latex_well_formed", "extract_sections", "extract_head_lines"]
