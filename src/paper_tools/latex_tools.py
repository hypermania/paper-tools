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

# TODO: functions for error message, subsections, paragraphs, etc

# parser = LatexLogParser()
# with open('slides.log', 'r') as f:
#     parser.process(f)
#     errors = parser.errors
# err_msgs = ["\n".join(error.context_lines) for error in errors]
# print(err_msgs[0])


# fix_latex_prompt = PromptTemplate(
#     input_variables=["latex", "error"],
#     template="""
#     You are a researcher writing a tex file.
#     By compiling the tex file with pdflatex, you found an error message in the log file.
#     Given the error message and the original latex file, output an tex file with the error fixed.
#     Make sure that the new tex file has the SAME CONTENT.
#     Provide ONLY the LaTeX output.

#     Error message:
#     {error}
    
#     LaTeX file:
#     {latex}
#     """
# )

# chain = fix_latex_prompt | llm_deepseek_r1
# with open('slides.tex', 'r') as f:
#     latex = f.read()
# response = chain.invoke({"latex": latex, "error": error_message})

# paper = r"""
# \begin{frame}[fragile]
# \frametitle{Auto-Verification Example}
# \begin{tcolorbox}
# \footnotesize
# \textbf{Problem Statement:}\\
# Photon scattering on electron at rest. Find scattered photon's angular frequency.

# \begin{lstlisting}[language=Python]
# def omega_scattered(E: float, m_e:float, theta:float, 
#                    c:float, h_bar:float) -> float:
#     pass
# \end{lstlisting}
# \end{tcolorbox}

# \begin{tcolorbox}
# \footnotesize
# \textbf{Solution:}
# \begin{equation*}
# \boxed{\omega = \frac{1}{\frac{\hbar}{E}+\frac{\hbar}{mc^2}(1-\cos{\theta})}}
# \end{equation*}
# \begin{lstlisting}[language=Python]
# import math
# def omega_scattered(E, m_e, theta, c, h_bar):
#     return 1/(h_bar/E + h_bar/(m_e*c**2)*(1-math.cos(theta)))
# \end{lstlisting}
# \end{tcolorbox}
# \end{frame}
# """

# my_latex_walker = latexwalker.LatexWalker(paper, tolerant_parsing=False)
# parsing_state = my_latex_walker.make_parsing_state()
# nodelist, parsing_state_delta = my_latex_walker.parse_content(
#     latexnodes.parsers.LatexGeneralNodesParser(),
#     parsing_state=parsing_state
# )
# npos = nodelist.pos
# nlen = nodelist.len # or nodelist.pos_end - nodelist.pos
