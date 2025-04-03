import os
from pathlib import Path
import numpy as np

mypath = str(Path(os.getcwd()) / "test_path")

import paper_tools.inspirehep_tools as ptools
e = ptools.EmbeddingLmdbWrapper(mypath,readonly=False)

vec = np.array([1,2,3,4], dtype=np.float16)

e['abc'] = vec
