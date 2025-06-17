# app.py
from flask import Flask, request, render_template
import json
import pipe
import numpy as np
import faiss
from FlagEmbedding import FlagAutoModel
from paper_tools.inspirehep_tools import *
from paper_tools.config import get_data_dir
from pathlib import Path

db_path = get_data_dir()
db = InspireHEPDatabase(db_path)

# need to change
with open(db_path / Path('all_abstracts.json'), 'r') as f:
    all_abstracts = json.load(f)
abstract_ids = list(all_abstracts)
abstract_id_to_idx = {i:abstract_ids[i] for i in range(len(abstract_ids))}
    
all_abstract_embeddings = np.load(db_path + 'all_abstract_embeddings_desktop.dat.npy')

index_faiss = faiss.IndexFlatIP(1024)
index_faiss.add(all_abstract_embeddings)

model = FlagAutoModel.from_finetuned('BAAI/bge-large-en-v1.5')


def search_similar_abstracts(query, k):
    my_embedding = model.encode_queries([query])
    D, I = index_faiss.search(my_embedding, k)

    close_ids = list(I.tolist()[0] | pipe.select(lambda idx: abstract_ids[idx]) )

    return [{
        'title': db.record[close_ids[i]]['metadata']['titles'][0]['title'],
        'authors': list(db.record[close_ids[i]]['metadata']['authors'] | pipe.select(lambda r: r['full_name'])),
        'date': db.record[close_ids[i]]['created'],
        'abstract': db.record[close_ids[i]]['metadata']['abstracts'][0]['value'],
        'score': D[0,i],
        'url': "https://inspirehep.net/literature/{}".format(close_ids[i])
    } for i in range(len(close_ids))]

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Get form data
        query_text = request.form['query']
        k = int(request.form['k'])

        print("query_text is {}".format(query_text))
        
        # Call your existing search backend
        results = search_similar_abstracts(query_text, k)
        
        return render_template('results.html', 
                             query=query_text,
                             results=results)
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
