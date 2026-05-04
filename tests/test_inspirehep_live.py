"""
Live integration test: query InspireHEP API for author Siyang Ling,
store records in LMDB database, and verify retrieval.
"""

import sys
import os
import tempfile
import shutil
import unittest
import json
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import paper_tools.inspirehep_tools as ptools


class TestInspireHEPLive(unittest.TestCase):
    """Live tests against the real InspireHEP API and local LMDB database."""

    AUTHOR_NAME = "Siyang Ling"
    EXPECTED_TEXKEY_PATTERN = "Ling:"

    @classmethod
    def setUpClass(cls):
        """Query InspireHEP API for records by Siyang Ling."""
        cls.client = ptools.InspireHEPClient()
        cls.author_ids = cls.client.get_id_by_author(cls.AUTHOR_NAME)
        cls.author_id_list = list(cls.author_ids)

    def test_api_get_id_by_author_returns_records(self):
        """InspireHEP API should return records for Siyang Ling."""
        self.assertIsInstance(self.author_id_list, list)
        self.assertGreater(len(self.author_id_list), 0,
                           f"No records found for author '{self.AUTHOR_NAME}'")
        self.assertTrue(all(isinstance(x, str) for x in self.author_id_list))
        print(f"\nFound {len(self.author_id_list)} InspireHEP records for {self.AUTHOR_NAME}")

    def test_api_get_literature_batched(self):
        """get_literature_batched should retrieve full records."""
        sample_ids = self.author_id_list[:5]
        result = self.client.get_literature_batched(sample_ids)
        for rid in sample_ids:
            self.assertIn(rid, result)
            record = result[rid]
            self.assertIn("metadata", record)
            self.assertIn("titles", record["metadata"])
        print(f"Retrieved {len(result)} full literature records")

    def test_api_get_bibtex_batched(self):
        """get_bibtex_batched should return BibTeX entries."""
        sample_ids = self.author_id_list[:5]
        bibtex_entries = self.client.get_bibtex_batched(sample_ids)
        self.assertGreater(len(bibtex_entries), 0)
        for entry in bibtex_entries:
            self.assertIn("@", entry)
        print(f"Retrieved {len(bibtex_entries)} BibTeX entries")

    def test_api_get_bibtex_single(self):
        """get_bibtex should return a single BibTeX entry."""
        if len(self.author_id_list) > 0:
            bibtex = self.client.get_bibtex(self.author_id_list[0])
            self.assertIn("@", bibtex)
            print(f"Single BibTeX entry length: {len(bibtex)} chars")

    def test_api_get_id_by_texkey(self):
        """get_id_by_texkey should map texkeys to InspireHEP IDs."""
        if len(self.author_id_list) > 0:
            # Grab one record to get its texkeys
            record = self.client.get_literature(self.author_id_list[0])
            texkeys = record["metadata"].get("texkeys", [])
            if texkeys:
                mapping = self.client.get_id_by_texkey(texkeys[:1])
                self.assertGreater(len(mapping), 0)
                texkey = texkeys[0]
                self.assertEqual(mapping[texkey], self.author_id_list[0])
                print(f"Texkey lookup: {texkey} -> {mapping[texkey]}")

    def test_local_database_store_and_retrieve(self):
        """Local LMDB database should store and retrieve InspireHEP records."""
        tmpdir = tempfile.mkdtemp()

        try:
            db = ptools.InspireHEPDatabase(path=tmpdir, readonly=False)

            # Store records
            sample_ids = self.author_id_list[:3]
            records = self.client.get_literature_batched(sample_ids)
            db.record.setitem_batched(records)

            # Verify records
            for rid in sample_ids:
                stored = db.record[rid]
                self.assertEqual(stored["id"], rid)
                self.assertIn("metadata", stored)
                self.assertIn("titles", stored["metadata"])
                title = stored["metadata"]["titles"][0]["title"]
                print(f"  Stored: {rid} -> {title}")

            # Store bibtex
            bibtex_map = {}
            for i, rid in enumerate(sample_ids):
                bibtex = self.client.get_bibtex(rid)
                bibtex_map[rid] = bibtex
            db.bibtex.setitem_batched(bibtex_map)

            # Verify bibtex
            for rid in sample_ids:
                stored_bibtex = db.bibtex[rid]
                self.assertIn("@", stored_bibtex)

            # Test iteration
            db_keys = list(db.record.keys())
            db_items = list(db.record.items())
            self.assertEqual(len(db_keys), len(sample_ids))
            self.assertEqual(len(db_items), len(sample_ids))

            # Test contains
            for rid in sample_ids:
                self.assertIn(rid, db.record)
            self.assertNotIn("nonexistent_id_999", db.record)

            print(f"LMDB database with {len(db.record)} records, "
                  f"{len(db.bibtex)} bibtex entries works correctly")

            db.record.env.close()
            db.bibtex.env.close()
            db.embedding.env.close()
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_embedding_database_store_and_retrieve(self):
        """EmbeddingLmdbWrapper should store and retrieve numpy arrays."""
        tmpdir = tempfile.mkdtemp()

        try:
            emb = ptools.EmbeddingLmdbWrapper(
                os.path.join(tmpdir, "emb.lmdb"),
                readonly=False, dtype=np.float16
            )
            vec = np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float16)
            emb["test_vec"] = vec
            stored = emb["test_vec"]
            self.assertTrue(np.allclose(vec, stored))
            self.assertEqual(len(emb), 1)
            self.assertIn("test_vec", emb)

            keys_list = list(emb.keys())
            self.assertEqual(keys_list, ["test_vec"])

            print(f"EmbeddingLmdbWrapper: stored {len(vec)}-dim vector, "
                  f"retrieved correctly")
            emb.env.close()
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
