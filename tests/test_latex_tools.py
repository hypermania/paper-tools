from paper_tools import latex_tools
import pipe



paper_path = "sample.tex"
with open(paper_path, 'r') as f:
    paper = f.read()
    
snippet = latex_tools.LatexSnippet(paper)
sections = snippet.get_sections()
paragraphs = snippet.get_paragraphs()
print(snippet.is_well_formed())
main_text = snippet.get_maintext()

with open('main_text.tex', 'w') as f:
    f.write(main_text)

# intervals = snippet.get_intervals(latex_tools.NontextVisitor, reverse=True)
# split_subtext = snippet.get_split_subtext(intervals)
# filtered_subtext = latex_tools.filter_empty(split_subtext)
# for i in range(len(split_subtext)):
#     print("INTERVAL {}:".format(i))
#     print(split_subtext[i])
#     print("=======================================================================================")

# well_formedness = list(paragraphs | pipe.select(lambda p: latex_tools.LatexSnippet(p).is_well_formed()))
