from pipe import Pipe #, where, select, sort, dedup, map
import pipe
import warnings
import datetime

# Custom pipe operators --------------------------------------------------------

get_id = pipe.select(lambda r: r[0])
get_title = pipe.select(lambda r: r[1]['metadata']['titles'][0]['title'])
get_type = pipe.select(lambda r: r[1]['metadata']['document_type'])
get_authors = pipe.select(lambda r: list(r[1]['metadata']['authors'] | pipe.select(lambda author: author['full_name'])))
get_citation_count = pipe.select(lambda r: r[1]['metadata']['citation_count'])

@Pipe
def get_abstract(record):
    for r in record:
        abstracts = r[1]['metadata'].get('abstracts')
        if abstracts:
            yield abstracts[0]['value']

@Pipe
def get_keywords(record):
    for r in record:
        keywords = r[1]['metadata'].get('keywords')
        if keywords:
            yield list(keywords | pipe.select(lambda k: k['value']))
        else:
            yield []

#get_keywords = pipe.select(lambda r: list(r[1]['metadata']['keywords'] | pipe.select(lambda keyword: keyword['value'])))
# get_abstract = pipe.select(lambda r: r[1]['metadata']['abstracts'][0]['value'])
# filter_abstract = pipe.where(lambda r: r[1]['metadata'].get('abstracts'))
# filter_abstract = pipe.where(lambda r: not r[1]['metadata'].get('abstracts'))
# filter_article = pipe.where(lambda r: 'article' in r[1]['metadata']['document_type'])
# get_types_len = pipe.select(lambda r: len(r[1]['metadata']['document_type']))
# filter_types_len = pipe.where(lambda r: len(r[1]['metadata']['document_type']) > 1)

@Pipe
def print_all(iterable):
    for item in iterable:
        print(item)
    
@Pipe
def filter_by_year(records, year):
    """Filter records by publication year"""
    return records | pipe.where(lambda r: datetime.datetime.fromisoformat(r[1].get('created')).year == year)

@Pipe
def filter_after(records, year, month, day):
    """Filter records by publication year"""
    dt = datetime.datetime(year, month, day, tzinfo=datetime.timezone.utc)
    return records | pipe.where(lambda r: datetime.datetime.fromisoformat(r[1].get('created')) >= dt)

@Pipe
def filter_before(records, year, month, day):
    """Filter records by publication year"""
    dt = datetime.datetime(year, month, day, tzinfo=datetime.timezone.utc)
    return records | pipe.where(lambda r: datetime.datetime.fromisoformat(r[1].get('created')) <= dt)

@Pipe
def filter_by_author(records, author_name):
    """Filter records by author name (case-insensitive)"""
    return records | pipe.where(lambda r: any(
        author_name.lower() in author['full_name'].lower()
        for author in r[1]['metadata'].get('authors', [])
    ))

@Pipe
def filter_by_title(records, keyword):
    """Filter records by title keyword"""
    return records | pipe.where(lambda r: any(
        keyword.lower() in title['title'].lower()
        for title in r[1]['metadata'].get('titles', [])
    ))

@Pipe
def filter_by_abstract(records, keyword):
    """Filter records by abstract keyword"""
    return records | pipe.where(lambda r: any(
        keyword.lower() in abstract['value'].lower()
        for abstract in r[1]['metadata'].get('abstracts', [])
    ))

@Pipe
def sort_by_citations(records, descending=True):
    """Sort records by citation count"""
    return records | pipe.sort(key=lambda r: r[1]['metadata'].get('citation_count', 0), reverse=descending)

@Pipe
def extract_fields(records, fields):
    """Extract specific fields from records"""
    return records | pipe.select(lambda r: {field: r[1]['metadata'].get(field) for field in fields})


@Pipe
def as_list(iterable):
    warnings.warn(
        "pipe.as_list is deprecated, use list(your | pipe) instead.",
        DeprecationWarning,
        stacklevel=4,
    )
    return list(iterable)

# @Pipe
# def limit_results(records, n):
#     """Limit to first N results"""
#     return records | select(lambda x: x) | dedup | select(lambda x: x)[:n]

# Example usage
list(wrapper.items() | filter_by_abstract('quasinormal mode') | filter_by_abstract('ringdown') | sort_by_citations() | pipe.take(5) | get_title)

list(wrapper.items() | filter_by_abstract('quasinormal mode') | filter_by_abstract('ringdown') | sort_by_citations() | pipe.take(5) | extract_fields(['titles']))

len(list(wrapper.items() | filter_before(2020,1,1) | filter_after(2015,1,1) | get_id))

# Example usage ----------------------------------------------------------------
#if __name__ == "__main__":
if True:
    # Convert dict to list of records for piping
    records = list(inspire_records.values())

    # Example 1: Basic search pipeline
    results = (records
        | filter_by_year(2020)
        | filter_by_title("dark matter")
        | extract_fields(['titles', 'citation_count'])
    )
    print("Recent dark matter papers:")
    for r in results:
        print(f"- {r['titles'][0]['title']} ({r['citation_count']} citations)")

    # Example 2: Complex query with sorting and limiting
    top_papers = (records
        | filter_by_year(2012)
        | sort_by_citations(descending=True)
        | limit_results(5)
        | extract_fields(['titles', 'citation_count', 'arxiv_eprints'])
    )
    
    print("\nTop cited papers from 2012:")
    for paper in top_papers:
        arxiv_id = paper['arxiv_eprints'][0]['value'] if paper.get('arxiv_eprints') else 'N/A'
        print(f"- {arxiv_id}: {paper['titles'][0]['title']}")

    # Example 3: Author search with multiple filters
    einstein_papers = (records
        | filter_by_author("Einstein")
        | filter_by_year(2020)
        | sort_by_citations()
        | extract_fields(['titles', 'publication_info'])
    )


records = list(inspire_records.values())

# Example 2: Complex query with sorting and limiting
top_papers = (records
              | filter_by_year(2012)
              | sort_by_citations(descending=True)
              #| limit_results(5)
              | extract_fields(['titles', 'citation_count', 'arxiv_eprints'])
              )
    
print("\nTop cited papers from 2012:")
for paper in top_papers:
    arxiv_id = paper['arxiv_eprints'][0]['value'] if paper.get('arxiv_eprints') else 'N/A'
    print(f"- {arxiv_id}: {paper['titles'][0]['title']}")
