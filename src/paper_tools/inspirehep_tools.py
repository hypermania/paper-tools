import requests
import json
import time
import re
import copy
import lmdb
import msgpack
import pathlib
import paper_tools.lmdb_wrapper as lmdb_wrapper
import pipe
from typing import List, Dict
import numpy as np
# import os
# from dotenv import load_dotenv
# import bibtexparser
# from thefuzz import fuzz
# import networkx as nx

# A wrapper around requests.
# Used to limit the rate of InspireHEP API calls.
class RateLimitedRequests:
    def __init__(self,
                 minimum_interval_s:float=0.4,
                 sleep_interval_s:float=0.1
                 ):
        self.last_requested_ns = time.time_ns()
        self.minimum_interval_ns = int(minimum_interval_s * 1e9)
        self.sleep_interval_s = sleep_interval_s
        return
    
    def get(self, query, **arg):
        while time.time_ns() - self.last_requested_ns < self.minimum_interval_ns:
            time.sleep(self.sleep_interval_s)
        print("QUERYING: {} WITH {}".format(query, json.dumps(arg)))
        response = requests.get(query, **arg)
        last_requested_ns = time.time_ns()
        return response


# Contains convenience functions for making InspireHEP API calls.
class InspireHEPClient:
    def __init__(self):
        self.rl_requests = RateLimitedRequests()

    
    """Get full record of particular literature using INSPIRE-HEP API"""
    def get_literature(self, inspire_id: str):
        response = self.rl_requests.get("https://inspirehep.net/api/literature/{}".format(inspire_id))
        return json.loads(response.content)


    """Search INSPIRE-HEP API and return BibTeX entries"""
    def get_literature_batched(self, id_list: List[str], max_results: int = 50) -> List[dict]:
        id_chunks = [id_list[i:i+max_results] for i in range(0, len(id_list), max_results)]
        
        calls = []
        for chunk in id_chunks:
            query = " or ".join(list(map(lambda r: "(control_number:{})".format(r), chunk)))
            params = {
                "q": query,
                "size": max_results,
                "sort": "mostcited"
            }
            response = self.rl_requests.get(
                "https://inspirehep.net/api/literature",
                params=params
            )
            response_dict = json.loads(response.content)
            calls.append(response_dict)

        result = {lit['id'] : lit for lit in calls | pipe.select(lambda c: c['hits']['hits']) | pipe.chain}
        return result


    """Search the InspireHEP id for given BibTeX keys"""
    def get_id_by_texkey(self, bibtex_list: List[str], max_results: int = 50) -> dict:
        bibtex_chunks = [bibtex_list[i:i+max_results] for i in range(0, len(bibtex_list), max_results)]
        
        calls = []
        for chunk in bibtex_chunks:
            query = " or ".join(list(map(lambda r: "(texkeys:{})".format(r), chunk)))
            params = {
                "q": query,
                "size": max_results,
                "sort": "mostcited",
                "fields": "texkeys"
            }
            response = self.rl_requests.get(
                "https://inspirehep.net/api/literature",
                params=params
            )
            response_dict = json.loads(response.content)
            calls.append(response_dict)
        
        result = dict()
        for call in calls:
            for record in call['hits']['hits']:
                for key in record['metadata']['texkeys']:
                    result[key] = record['id']
            
        return result


    """Search the InspireHEP id for given author"""
    def get_id_by_author(self, author: str, max_results: int = 50) -> dict:
        calls = []
        
        def call_api(page_num):
            params = {
                "q": "authors.full_name:{}".format(author),
                "size": max_results,
                "sort": "mostrecent",
                "fields": "authors",
                "page": page_num
            }
            response = self.rl_requests.get("https://inspirehep.net/api/literature",
                                            params=params)
            calls.append(json.loads(response.content))
            #print(len(calls[-1]['hits']['hits']))

        page_num = 1
        call_api(page_num)
        total = calls[-1]['hits']['total']
        found = len(calls[-1]['hits']['hits'])
        while found < total:
            page_num += 1
            call_api(page_num)
            found += len(calls[-1]['hits']['hits'])

        result = list(calls | pipe.select(lambda c: c['hits']['hits']) | pipe.chain | pipe.select(lambda r: r['id']))
        return result
    

    """Get BibTeX entry of particular literature using INSPIRE-HEP API"""
    def get_bibtex(self, inspire_id: str) -> str:
        # Use content negoatiation
        response = self.rl_requests.get("https://inspirehep.net/api/literature/{}".format(inspire_id),
                                        headers={"Accept": "application/x-bibtex"})
        return response.content.decode()

    
    """Get BibTeX entry of a list of literature using INSPIRE-HEP API"""
    def get_bibtex_batched(self, id_list: List[str], max_results : int = 100) -> List[str]:
        id_chunks = [id_list[i:i+max_results] for i in range(0, len(id_list), max_results)]
        
        calls = []
        for chunk in id_chunks:
            query = " or ".join(list(map(lambda r: "(control_number:{})".format(r), chunk)))
            params = {
                "q": query,
                "size": max_results,
                "sort": "mostcited",
                "format": "bibtex"
            }
            response = self.rl_requests.get(
                "https://inspirehep.net/api/literature",
                params=params
            )
            calls.append(response.content.decode())
        
        result = []
        for call in calls:
            result.extend(call.split('\n\n'))
        
        return result

    
    """Get id of all cites to a particular literature using INSPIRE-HEP API"""
    def all_cites_to(self, inspire_id: str, max_results: int = 200) -> List[str]:
        calls = []
        
        def call_api(page_num):
            params = {
                "q": "refersto:recid:{}".format(inspire_id),
                "size": max_results,
                "sort": "mostrecent",
                "fields": "id", # not really a valid field
                "page": page_num
            }
            response = self.rl_requests.get("https://inspirehep.net/api/literature",
                                            params=params)
            calls.append(json.loads(response.content))

        page_num = 1
        call_api(page_num)
        total = calls[-1]['hits']['total']
        found = len(calls[-1]['hits']['hits'])
        while found < total:
            page_num += 1
            call_api(page_num)
            found += len(calls[-1]['hits']['hits'])

        result = list(calls | pipe.select(lambda c: c['hits']['hits']) | pipe.chain | pipe.select(lambda r: r['id']))
        return result

    """Get id of all cites to a list of literature using INSPIRE-HEP API"""
    def all_cites_to_batched(self, inspire_ids: List[str], max_results: int = 200) -> List[str]:
        calls = []
        query = " or ".join(list(map(lambda r: "(refersto:recid:{})".format(r), inspire_ids)))        
        def call_api(page_num):
            params = {
                "q": query,
                "size": max_results,
                "sort": "mostrecent",
                "fields": "id", # not really a valid field
                "page": page_num
            }
            response = self.rl_requests.get("https://inspirehep.net/api/literature",
                                            params=params)
            calls.append(json.loads(response.content))

        page_num = 1
        call_api(page_num)
        total = calls[-1]['hits']['total']
        found = len(calls[-1]['hits']['hits'])
        while found < total:
            page_num += 1
            call_api(page_num)
            found += len(calls[-1]['hits']['hits'])

        result = list(calls | pipe.select(lambda c: c['hits']['hits']) | pipe.chain | pipe.select(lambda r: r['id']))
        return result

    
    def search(self, query: str, max_results=50):
        params = {
            "q": query,
            "size": max_results,
            "sort": "mostcited"
        }
        response = self.rl_requests.get(
            "https://inspirehep.net/api/literature",
            params=params
        )
        return response
    


# Fuzzy match over InspireHEP records.
def fuzzy_match_inspirehep_record(record: dict, keyword: str):
    title = record['metadata']['titles'][0]['title']
    abstracts = record['metadata'].get('abstracts')
    keywords = record['metadata'].get('keywords')
    authors = record['metadata'].get('authors')

    max_score = fuzz.partial_ratio(keyword, title)
    if abstracts != None:
        max_score = max(max_score, fuzz.partial_ratio(keyword, abstracts[0]['value']))
    if keywords != None and len(keywords) > 0:
        max_score = max(max_score, max(map(lambda word: fuzz.partial_ratio(keyword, word['value']), keywords)))
    if authors != None and len(authors) > 0:
        max_score = max(max_score, max(authors | pipe.select(lambda a: fuzz.partial_ratio(a['full_name'], keyword))))

    return max_score


# Not very useful. Just for fun.
class InspireHEPAnalytics:
    # Initialize an empty collection
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
        #return sorted(pr.items(), key=lambda x: -x[1])
        return {x[0]: x[1] for x in pr.items()}

    def fuzzy_search_inspirehep_collection(self, search_term, threshold=90):
        collection = self.collection
        results = []
        search_term = search_term.lower().strip()
    
        for key, value in collection.items():
            score = fuzzy_match_inspirehep_record(value, search_term)
            if score >= threshold:
                results.append((key, score))
    
        return sorted(results, key=lambda x: x[1], reverse=True)



class InspireHEPRecordLmdbWrapper(lmdb_wrapper.LmdbWrapperBase):
    def pack_value(self, value: dict) -> bytes:
        return msgpack.packb(value)
    def unpack_value(self, value: bytes) -> dict:
        return msgpack.unpackb(value)


class InspireHEPBibtexLmdbWrapper(lmdb_wrapper.LmdbWrapperBase):
    def pack_value(self, value: str) -> bytes:
        return value.encode()
    def unpack_value(self, value: bytes) -> str:
        return value.decode()


class EmbeddingLmdbWrapper(lmdb_wrapper.LmdbWrapperBase):
    def __init__(self, dtype=np.dtype('float16'), **kwargs):
        self.dtype = dtype
        super().__init__(kwargs)
    def pack_value(self, value: numpy.ndarray) -> bytes:
        return np.tobytes(value)
    def unpack_value(self, value: bytes) -> numpy.ndarray:
        return np.frombuffer(value, dtype=self.dtype)

    
# Database manager for InspireHEP records and bibtex items
class InspireHEPDatabase:
    RECORD_NAME = "record.lmdb"
    BIBTEX_NAME = "bibtex.lmdb"
    
    def __init__(self,
                 path:str,
                 map_size:int=10737418240,  # Default 10GB
                 readonly:bool=True):
        record_path = str(pathlib.Path(path) / self.RECORD_NAME)
        bibtex_path = str(pathlib.Path(path) / self.BIBTEX_NAME)
        
        # 10 GB default map_size
        self.record = InspireHEPRecordLmdbWrapper(record_path, map_size=map_size, readonly=readonly)
        self.bibtex = InspireHEPBibtexLmdbWrapper(bibtex_path, map_size=map_size, readonly=readonly)



# BFS search download literature works
def inspirehep_bfs_literature(collection: dict, roots: List[str], max_size: int, mode: str = "refs"):
    re_extract_id = re.compile('/([0-9]+)$')
    
    queue = copy.deepcopy(roots)
    while len(collection) < max_size and len(queue) > 0:
        inspire_id = queue.pop(0)
        if inspire_id in collection:
            literature_json = collection[inspire_id]
            #print("Already have reference, skipping\n")
        else:
            literature_json = client.get_literature(inspire_id)
            collection[inspire_id] = literature_json
            print("Got new reference: {}\nID: {}\n".format(literature_json['metadata']['titles'], literature_json['id']))

        references = literature_json['metadata'].get('references')
        if references == None:
            continue
        for ref in references:
            if ref.get('record') == None:
                continue
            ref_id = re_extract_id.findall(ref['record']['$ref'])[0]
            if ref_id not in queue:
                queue.append(ref_id)


def reference_ids(record: dict):
    references = record['metadata'].get('references')
    # print(references[0]['record']['$ref'])
    if references == None:
        return []
    else:
        re_extract_id = re.compile('/([0-9]+)$')
        return list(references | pipe.filter(lambda r: r.get('record') != None) | pipe.select(lambda r: re_extract_id.findall(r['record']['$ref'])[0]))
    

# Batched BFS search download literature works
def inspirehep_bfs_literature_batch(collection: dict, roots: List[str], max_size: int, mode: str = "refs", batch: int = 50):
    client = InspireHEPClient()
    queue = copy.deepcopy(roots)
    while len(collection) < max_size and len(queue) > 0:
        inspire_ids = queue[:batch]
        queue = queue[len(inspire_ids):]
        ids_to_grab = list(inspire_ids | pipe.filter(lambda i: i not in collection))
        grabbed = client.get_literature_batched(ids_to_grab)
        records = list(inspire_ids | pipe.select(lambda i: grabbed[i] if (i in grabbed) else collection[i]))
        for record in records:
            if record['id'] not in collection:
                collection[record['id']] = record
        
        if mode == "refs":
            branch_ids = set(records | pipe.select(reference_ids) | pipe.chain)
        elif mode == "cites":
            branch_ids = set(client.all_cites_to_batched(list(records | pipe.select(lambda r: r['id']))))
        elif mode == "both":
            branch_ids = set(records | pipe.select(reference_ids) | pipe.chain) | set(client.all_cites_to_batched(list(records | pipe.select(lambda r: r['id']))))

        not_in_queue = branch_ids - set(queue)
        queue.extend(list(not_in_queue))
        
        print("Downloaded {} new InspireHEP records. {} ids in queue.".format(len(grabbed), len(queue)))



__all__ = ["InspireHEPClient", "InspireHEPDatabase"]
