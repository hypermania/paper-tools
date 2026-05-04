import re
import networkx as nx


# Citation graph analytics over an InspireHEP record collection.
# Provides graph construction and PageRank computation for a set of literature records.
class InspireHEPAnalytics:
    def __init__(self, collection):
        self.collection = collection

    def make_citation_graph(self):
        collection = self.collection
        re_extract_id = re.compile('/([0-9]+)$')
        graph = dict()
        for record_id, record in collection.items():
            graph[record_id] = []
            references = record['metadata'].get('references')
            if references == None:
                continue
            for ref in references:
                if ref.get('record') == None:
                    continue
                ref_id = re_extract_id.findall(ref['record']['$ref'])[0]
                graph[record_id].append(ref_id)
        return graph

    def compute_pagerank(self, alpha=0.85, max_iter=100):
        G = nx.DiGraph()

        graph = self.make_citation_graph()
        for lit_id, lit_cites in graph.items():
            # Add edges: paper -> cited_paper
            for cite_id in lit_cites:
                if cite_id in graph:  # Only track papers in our initial set
                    G.add_edge(lit_id, cite_id)
                    G.add_edge(cite_id, lit_id)

        pr = nx.pagerank(G, alpha=alpha, max_iter=max_iter)
        return {x[0]: x[1] for x in pr.items()}


__all__ = ["InspireHEPAnalytics"]
