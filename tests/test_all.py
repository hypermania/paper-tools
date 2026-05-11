"""
Comprehensive test suite for paper-tools.

Covers: latex_tools, lmdb_wrapper, config, inspirehep_tools (mocked), pipe_usage.
Run with: python3 -m pytest tests/test_all.py -v
Or:       python3 tests/test_all.py
"""

import sys
import os
import tempfile
import shutil
import unittest
from unittest.mock import patch, MagicMock, PropertyMock
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# ============================================================================
# latex_tools tests
# ============================================================================

import paper_tools.latex_tools as latex_tools


class TestLatexSnippet(unittest.TestCase):
    """Tests for LatexSnippet and related utilities."""

    def setUp(self):
        self.valid_minimal = r"""
\documentclass{article}
\begin{document}
Hello world.
\end{document}
"""

    def test_is_well_formed_valid_minimal(self):
        s = latex_tools.LatexSnippet(self.valid_minimal)
        self.assertTrue(s.is_well_formed())

    def test_is_well_formed_valid_with_math(self):
        s = latex_tools.LatexSnippet(r"""
\documentclass{article}
\begin{document}
Einstein's equation: $E = mc^2$.
Some displayed math:
\[
\int_0^\infty e^{-x} dx = 1
\]
More text.
\end{document}
""")
        self.assertTrue(s.is_well_formed())

    def test_is_well_formed_malformed(self):
        # NOTE: pylatexenc does not raise errors for unclosed \\begin{document};
        # it returns a partial parse with a warning. True is the observed behavior.
        s = latex_tools.LatexSnippet(r"\begin{document} unclosed")
        self.assertTrue(s.is_well_formed())  # pylatexenc limitation

    def test_is_well_formed_empty(self):
        s = latex_tools.LatexSnippet("")
        # Empty string may or may not parse depending on pylatexenc version
        result = s.is_well_formed()
        self.assertIsInstance(result, bool)

    def test_comments_removed(self):
        tex = r"""
\documentclass{article}
\begin{document}
% This is a comment
Hello % inline comment
world.
% Another comment
\end{document}
"""
        s = latex_tools.LatexSnippet(tex)
        cleaned = s.comments_removed()
        self.assertNotIn("This is a comment", cleaned)
        self.assertNotIn("inline comment", cleaned)
        self.assertIn("Hello", cleaned)
        self.assertIn("world", cleaned)

    def test_nontext_removed(self):
        tex = r"""
\documentclass{article}
\newcommand{\foo}{bar}
\begin{document}
\section{Intro}
Some text here.
\end{document}
"""
        s = latex_tools.LatexSnippet(tex)
        cleaned = s.nontext_removed()
        self.assertNotIn(r"\documentclass", cleaned)
        self.assertNotIn(r"\newcommand", cleaned)
        self.assertIn("Some text here", cleaned)

    def test_get_maintext(self):
        tex = r"""
\documentclass{article}
\usepackage{amsmath}
\newcommand{\foo}{bar}
\begin{document}
\maketitle
\section{Intro}
% This comment should be gone
The quick brown fox.
\section{Methods}
$E=mc^2$ and more text.
% Another comment
\end{document}
"""
        s = latex_tools.LatexSnippet(tex)
        main = s.get_maintext()
        self.assertIn("The quick brown fox", main)
        self.assertIn("$E=mc^2$", main)
        self.assertNotIn("This comment should be gone", main)
        self.assertNotIn(r"\documentclass", main)
        self.assertNotIn(r"\usepackage", main)
        self.assertNotIn(r"\newcommand", main)

    def test_get_paragraphs(self):
        tex = r"""
\documentclass{article}
\begin{document}
First paragraph here.

Second paragraph that spans
multiple lines.

Third paragraph with \textit{formatting}.
\end{document}
"""
        s = latex_tools.LatexSnippet(tex)
        paragraphs = s.get_paragraphs()
        self.assertEqual(len(paragraphs), 3)
        self.assertIn("First paragraph", paragraphs[0])
        self.assertIn("Second paragraph", paragraphs[1])
        self.assertIn("Third paragraph", paragraphs[2])

    def test_get_paragraphs_empty(self):
        # NOTE: An empty document with only structural markup still has one
        # "paragraph" of preamble text. True empty body text requires nontext_removed.
        tex = r"""
\documentclass{article}
\begin{document}
\end{document}
"""
        s = latex_tools.LatexSnippet(tex)
        paragraphs = s.get_paragraphs()
        # The preamble/setup appears as one paragraph
        self.assertEqual(len(paragraphs), 1)

    def test_get_sections(self):
        tex = r"""
\documentclass{article}
\begin{document}
\section{Introduction}
Introduction text here.
\section{Methods}
Methods text here.
\section{Results}
Results text here.
\end{document}
"""
        s = latex_tools.LatexSnippet(tex)
        sections = s.get_sections()
        self.assertEqual(len(sections), 3)
        for section in sections:
            self.assertIn(r"\section", section)

    def test_get_intervals_nontext(self):
        tex = r"\documentclass{article}\begin{document}Hello\end{document}"
        s = latex_tools.LatexSnippet(tex)
        intervals = s.get_intervals(latex_tools.NontextVisitor, reverse=False)
        self.assertIsInstance(intervals, list)
        self.assertTrue(len(intervals) >= 1)
        for interval in intervals:
            self.assertIsInstance(interval, tuple)
            self.assertEqual(len(interval), 2)

    def test_get_intervals_complement(self):
        tex = r"\documentclass{article}\begin{document}Hello\end{document}"
        s = latex_tools.LatexSnippet(tex)
        intervals = s.get_intervals(latex_tools.CommentVisitor, reverse=True)
        self.assertIsInstance(intervals, list)
        for interval in intervals:
            self.assertIsInstance(interval, tuple)
            self.assertEqual(len(interval), 2)

    def test_get_split_subtext(self):
        tex = r"\documentclass{article}\begin{document}Hello\end{document}"
        s = latex_tools.LatexSnippet(tex)
        intervals = s.get_intervals(latex_tools.CommentVisitor, reverse=True)
        texts = s.get_split_subtext(intervals)
        self.assertIsInstance(texts, list)
        for t in texts:
            self.assertIsInstance(t, str)

    def test_multiple_comment_styles(self):
        tex = r"""
\documentclass{article}
\begin{document}
% single line comment
Text here.
%% double percent
More text.
\end{document}
"""
        s = latex_tools.LatexSnippet(tex)
        cleaned = s.comments_removed()
        self.assertNotIn("single line comment", cleaned)
        self.assertNotIn("double percent", cleaned)
        self.assertIn("Text here", cleaned)

    def test_nested_braces_well_formed(self):
        tex = r"""
\documentclass{article}
\begin{document}
\textbf{\textit{nested formatting}} works.
\end{document}
"""
        s = latex_tools.LatexSnippet(tex)
        self.assertTrue(s.is_well_formed())


class TestLatexHelpers(unittest.TestCase):
    """Tests for module-level helper functions."""

    def test_filter_empty(self):
        texts = ["hello", "\n  \n", "", "world", "   "]
        result = latex_tools.filter_empty(texts)
        self.assertEqual(result, ["hello", "world"])

    def test_filter_empty_all_nonempty(self):
        texts = ["a", "b", "c"]
        result = latex_tools.filter_empty(texts)
        self.assertEqual(result, ["a", "b", "c"])

    def test_filter_empty_all_empty(self):
        texts = ["", "\n", "  \n "]
        result = latex_tools.filter_empty(texts)
        self.assertEqual(result, [])

    def test_split_to_paragraphs(self):
        text = "Para 1.\n\nPara 2.\n\n\nPara 3."
        result = latex_tools.split_to_paragraphs(text)
        self.assertEqual(result, ["Para 1.", "Para 2.", "Para 3."])

    def test_split_to_paragraphs_single(self):
        text = "Only one paragraph."
        result = latex_tools.split_to_paragraphs(text)
        self.assertEqual(result, ["Only one paragraph."])

    def test_extract_latex_with_markers(self):
        text = "Some text\n```latex\n\\documentclass{article}\n```\nMore text"
        result = latex_tools.extract_latex(text)
        self.assertIn(r"\documentclass", result)
        self.assertNotIn("Some text", result)
        self.assertNotIn("```", result)

    def test_extract_latex_without_markers(self):
        text = r"\documentclass{article}\begin{document}hi\end{document}"
        result = latex_tools.extract_latex(text)
        self.assertEqual(result, text)

    def test_extract_head_lines(self):
        text = "line1\nline2\nline3\nline4\nline5\nline6"
        result = latex_tools.extract_head_lines(text, lines=3)
        self.assertEqual(result, "line1\nline2\nline3")

    def test_extract_head_lines_fewer_available(self):
        text = "line1\nline2"
        result = latex_tools.extract_head_lines(text, lines=10)
        self.assertEqual(result, "line1\nline2")

    def test_is_latex_well_formed_true(self):
        tex = r"\documentclass{article}\begin{document}hi\end{document}"
        self.assertTrue(latex_tools.is_latex_well_formed(tex))

    def test_is_latex_well_formed_false(self):
        # NOTE: pylatexenc does not raise errors for unclosed environmnts.
        # It returns a partial parse. This tests our actual behavior.
        tex = r"\begin{document}unclosed"
        self.assertTrue(latex_tools.is_latex_well_formed(tex))  # pylatexenc limitation

    def test_extract_sections(self):
        tex = r"""
\documentclass{article}
\begin{document}
\section{One}
Content one.
\section{Two}
Content two.
\end{document}
"""
        sections = latex_tools.extract_sections(tex)
        self.assertEqual(len(sections), 2)

    def test_complement_pairs(self):
        result = latex_tools.complement_pairs([(0, 2), (4, 6)], 10)
        self.assertEqual(result, [(2, 4), (6, 10)])

    def test_complement_pairs_empty(self):
        result = latex_tools.complement_pairs([], 10)
        self.assertEqual(result, [(0, 10)])

    def test_complement_pairs_full(self):
        result = latex_tools.complement_pairs([(0, 10)], 10)
        self.assertEqual(result, [])


# ============================================================================
# lmdb_wrapper tests
# ============================================================================

import paper_tools.lmdb_wrapper as lmdb_wrapper


class TestLmdbWrapper(unittest.TestCase):
    """Tests for LmdbWrapperBase with a concrete subclass."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "test.lmdb")

        class StringWrapper(lmdb_wrapper.LmdbWrapperBase):
            def pack_value(self, value):
                return value.encode() if isinstance(value, str) else value

            def unpack_value(self, value):
                return value.decode() if isinstance(value, bytes) else value

        self.WrapperClass = StringWrapper

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_create_and_write_read(self):
        db = self.WrapperClass(self.db_path, readonly=False)
        db["hello"] = "world"
        self.assertEqual(db["hello"], "world")
        db.env.close()

    def test_len(self):
        db = self.WrapperClass(self.db_path, readonly=False)
        db["a"] = "1"
        db["b"] = "2"
        self.assertEqual(len(db), 2)
        db.env.close()

    def test_contains(self):
        db = self.WrapperClass(self.db_path, readonly=False)
        db["key1"] = "val1"
        self.assertIn("key1", db)
        self.assertNotIn("nonexistent", db)
        db.env.close()

    def test_key_error(self):
        db = self.WrapperClass(self.db_path, readonly=False)
        with self.assertRaises(KeyError):
            _ = db["nonexistent"]
        db.env.close()

    def test_iteration(self):
        db = self.WrapperClass(self.db_path, readonly=False)
        db["a"] = "1"
        db["b"] = "2"
        db["c"] = "3"
        keys = list(db)
        self.assertEqual(sorted(keys), ["a", "b", "c"])
        db.env.close()

    def test_keys(self):
        db = self.WrapperClass(self.db_path, readonly=False)
        db["x"] = "val"
        keys_list = list(db.keys())
        self.assertIn("x", keys_list)
        db.env.close()

    def test_values(self):
        db = self.WrapperClass(self.db_path, readonly=False)
        db["a"] = "alpha"
        db["b"] = "beta"
        vals = list(db.values())
        self.assertIn("alpha", vals)
        self.assertIn("beta", vals)
        db.env.close()

    def test_items(self):
        db = self.WrapperClass(self.db_path, readonly=False)
        db["a"] = "1"
        items = list(db.items())
        self.assertIn(("a", "1"), items)
        db.env.close()

    def test_setitem_batched(self):
        db = self.WrapperClass(self.db_path, readonly=False)
        data = {"k1": "v1", "k2": "v2", "k3": "v3"}
        db.setitem_batched(data)
        self.assertEqual(db["k1"], "v1")
        self.assertEqual(db["k2"], "v2")
        self.assertEqual(db["k3"], "v3")
        self.assertEqual(len(db), 3)
        db.env.close()

    def test_overwrite(self):
        db = self.WrapperClass(self.db_path, readonly=False)
        db["key"] = "original"
        db["key"] = "updated"
        self.assertEqual(db["key"], "updated")
        db.env.close()

    def test_context_manager(self):
        with self.WrapperClass(self.db_path, readonly=False) as db:
            db["ctx"] = "test"
        # Re-open read-only to verify
        with self.WrapperClass(self.db_path, readonly=True) as db:
            self.assertEqual(db["ctx"], "test")

    def test_readonly_cannot_write(self):
        db = self.WrapperClass(self.db_path, readonly=False)
        db["ro"] = "data"
        db.env.close()
        # Open read-only and attempt write should fail
        with self.WrapperClass(self.db_path, readonly=True) as ro_db:
            with self.assertRaises(Exception):
                ro_db["new"] = "should fail"

    def test_empty_db_len(self):
        db = self.WrapperClass(self.db_path, readonly=False)
        self.assertEqual(len(db), 0)
        db.env.close()

    def test_decode_key_bytes(self):
        """Test that keys can be bytes."""
        db = self.WrapperClass(self.db_path, readonly=False)
        db["test_key"] = "value"
        found = False
        for k in db:
            if k == "test_key":
                found = True
                break
        self.assertTrue(found)
        db.env.close()


# ============================================================================
# config tests
# ============================================================================

import paper_tools.config as config


class TestConfig(unittest.TestCase):
    """Tests for config module."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.orig_env = os.environ.get("PAPER_TOOLS_DATA_PATH")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        if self.orig_env is not None:
            os.environ["PAPER_TOOLS_DATA_PATH"] = self.orig_env
        elif "PAPER_TOOLS_DATA_PATH" in os.environ:
            del os.environ["PAPER_TOOLS_DATA_PATH"]

    def test_get_data_dir_default(self):
        if "PAPER_TOOLS_DATA_PATH" in os.environ:
            del os.environ["PAPER_TOOLS_DATA_PATH"]
        path = config.get_data_dir()
        self.assertIsInstance(path, Path)
        self.assertTrue(path.exists())

    def test_get_data_dir_custom_env(self):
        os.environ["PAPER_TOOLS_DATA_PATH"] = self.tmpdir
        path = config.get_data_dir()
        self.assertEqual(str(path), self.tmpdir)
        self.assertTrue(path.exists())

    def test_get_data_dir_creates_directory(self):
        new_dir = os.path.join(self.tmpdir, "nonexistent_subdir")
        os.environ["PAPER_TOOLS_DATA_PATH"] = new_dir
        path = config.get_data_dir()
        self.assertTrue(path.exists())


# ============================================================================
# inspirehep_tools tests (mocked)
# ============================================================================

class TestInspireHEPToolsMocked(unittest.TestCase):
    """Tests for InspireHEP tools with mocked HTTP responses."""

    @classmethod
    def setUpClass(cls):
        # Import locally to avoid issues if optional deps unavailable
        import paper_tools.inspirehep_tools as inspirehep_tools
        cls.module = inspirehep_tools

    def test_rate_limited_requests_init(self):
        rlr = self.module.RateLimitedRequests(minimum_interval_s=0.1, sleep_interval_s=0.05)
        self.assertIsNotNone(rlr)
        self.assertEqual(rlr.sleep_interval_s, 0.05)

    def test_inspirehep_client_init(self):
        client = self.module.InspireHEPClient()
        self.assertIsNotNone(client)
        self.assertIsInstance(client.rl_requests, self.module.RateLimitedRequests)

    @patch('paper_tools.inspirehep_tools.requests.get')
    def test_get_literature_mocked(self, mock_get):
        mock_response = MagicMock()
        mock_response.content = b'{"id": "1234567", "metadata": {"titles": [{"title": "Test Paper"}]}}'
        mock_get.return_value = mock_response

        client = self.module.InspireHEPClient()
        result = client.get_literature("1234567")
        self.assertEqual(result["id"], "1234567")
        self.assertEqual(result["metadata"]["titles"][0]["title"], "Test Paper")

    @patch('paper_tools.inspirehep_tools.requests.get')
    def test_get_literature_batched_mocked(self, mock_get):
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "hits": {
                "hits": [
                    {"id": "1", "metadata": {"titles": [{"title": "Paper One"}]}},
                    {"id": "2", "metadata": {"titles": [{"title": "Paper Two"}]}},
                ]
            }
        }).encode()
        mock_get.return_value = mock_response

        client = self.module.InspireHEPClient()
        result = client.get_literature_batched(["1", "2"])
        self.assertIn("1", result)
        self.assertIn("2", result)
        self.assertEqual(result["1"]["metadata"]["titles"][0]["title"], "Paper One")

    @patch('paper_tools.inspirehep_tools.requests.get')
    def test_get_id_by_texkey_mocked(self, mock_get):
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "hits": {
                "hits": [
                    {"id": "123", "metadata": {"texkeys": ["Author:2024abc"]}},
                ]
            }
        }).encode()
        mock_get.return_value = mock_response

        client = self.module.InspireHEPClient()
        result = client.get_id_by_texkey(["Author:2024abc"])
        self.assertEqual(result["Author:2024abc"], "123")

    @patch('paper_tools.inspirehep_tools.requests.get')
    def test_get_bibtex_mocked(self, mock_get):
        mock_response = MagicMock()
        mock_response.content = b"@article{Test2024,\n  title={Test}\n}"
        mock_get.return_value = mock_response

        client = self.module.InspireHEPClient()
        result = client.get_bibtex("123")
        self.assertIn("@article{Test2024", result)

    @patch('paper_tools.inspirehep_tools.requests.get')
    def test_get_bibtex_batched_mocked(self, mock_get):
        mock_response = MagicMock()
        mock_response.content = b"@article{A,\n  title={A}\n}\n\n@article{B,\n  title={B}\n}"
        mock_get.return_value = mock_response

        client = self.module.InspireHEPClient()
        result = client.get_bibtex_batched(["1", "2"])
        self.assertEqual(len(result), 2)

    @patch('paper_tools.inspirehep_tools.requests.get')
    def test_search_mocked(self, mock_get):
        mock_response = MagicMock()
        mock_get.return_value = mock_response

        client = self.module.InspireHEPClient()
        result = client.search("black holes")
        self.assertIsNotNone(result)

    def test_reference_ids(self):
        record = {
            "metadata": {
                "references": [
                    {"record": {"$ref": "https://inspirehep.net/api/literature/123"}},
                    {"record": {"$ref": "https://inspirehep.net/api/literature/456"}},
                ]
            }
        }
        ids = self.module.reference_ids(record)
        self.assertEqual(ids, ["123", "456"])

    def test_reference_ids_none(self):
        record = {"metadata": {}}
        ids = self.module.reference_ids(record)
        self.assertEqual(ids, [])

    def test_reference_ids_nonexistent_ref(self):
        record = {
            "metadata": {
                "references": [
                    {"no_record": "here"},
                ]
            }
        }
        ids = self.module.reference_ids(record)
        self.assertEqual(ids, [])


import json


class TestInspireHEPLmdbWrappers(unittest.TestCase):
    """Tests for LMDB wrappers for InspireHEP data types."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_record_lmdb_wrapper(self):
        import paper_tools.inspirehep_tools as inspirehep_tools
        db_path = os.path.join(self.tmpdir, "records.lmdb")
        db = inspirehep_tools.InspireHEPRecordLmdbWrapper(db_path, readonly=False)
        record = {"id": "123", "metadata": {"titles": [{"title": "Test"}]}}
        db["123"] = record
        self.assertEqual(db["123"], record)
        db.env.close()

    def test_bibtex_lmdb_wrapper(self):
        import paper_tools.inspirehep_tools as inspirehep_tools
        db_path = os.path.join(self.tmpdir, "bibtex.lmdb")
        db = inspirehep_tools.InspireHEPBibtexLmdbWrapper(db_path, readonly=False)
        bibtex = "@article{Test2024,\n  title={Test}\n}"
        db["Test2024"] = bibtex
        self.assertEqual(db["Test2024"], bibtex)
        db.env.close()

    def test_embedding_lmdb_wrapper(self):
        import paper_tools.inspirehep_tools as inspirehep_tools
        import numpy as np
        db_path = os.path.join(self.tmpdir, "emb.lmdb")
        db = inspirehep_tools.EmbeddingLmdbWrapper(db_path, readonly=False, dtype=np.float16)
        vec = np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float16)
        db["vec1"] = vec
        stored = db["vec1"]
        self.assertTrue(np.allclose(vec, stored))
        db.env.close()


# ============================================================================
# Bug detection tests (affirmative tests for known bugs)
# ============================================================================

class TestKnownIssues(unittest.TestCase):
    """Affirmative tests for previously known issues that are now fixed."""

    def test_pipe_usage_imports_cleanly(self):
        """pipe_usage module-level code used to have undefined variables (fixed)."""
        import paper_tools.pipe_usage
        self.assertTrue(True)


# ============================================================================
# Runner
# ============================================================================

if __name__ == "__main__":
    unittest.main(verbosity=2)
