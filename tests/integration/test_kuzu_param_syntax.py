"""Smoke tests that verify which Kùzu parameter patterns actually work.

These tests use the raw kuzu Connection (not KuzuAdapter) to isolate
parameter-syntax support from adapter logic.  Results are read via
get_next() rather than get_as_df() to avoid the pandas dependency.
"""

import kuzu
import pytest


def _fetch_all(result) -> list[dict]:
    """Drain a kuzu QueryResult into a list of dicts."""
    rows = []
    while result.has_next():
        row = result.get_next()
        cols = [result.get_column_names()[i] for i in range(len(row))]
        rows.append(dict(zip(cols, row, strict=True)))
    return rows


@pytest.fixture
def kuzu_db(tmp_path):
    db = kuzu.Database(str(tmp_path / "test.db"))
    conn = kuzu.Connection(db)
    conn.execute(
        "CREATE NODE TABLE IF NOT EXISTS Mem (id STRING PRIMARY KEY, val FLOAT DEFAULT 0.0)"
    )
    conn.execute("CREATE NODE TABLE IF NOT EXISTS Kw (word STRING PRIMARY KEY)")
    conn.execute("CREATE REL TABLE IF NOT EXISTS HAS_KW (FROM Mem TO Kw, tfidf FLOAT DEFAULT 0.0)")
    conn.execute("CREATE (:Mem {id: 'm1', val: 0.8})")
    conn.execute("CREATE (:Mem {id: 'm2', val: 0.6})")
    conn.execute("CREATE (:Kw {word: 'python'})")
    conn.execute("CREATE (:Kw {word: 'async'})")
    conn.execute(
        "MATCH (m:Mem {id: 'm1'}), (k:Kw {word: 'python'}) CREATE (m)-[:HAS_KW {tfidf: 0.9}]->(k)"
    )
    yield conn


def test_in_list_param(kuzu_db):
    """Does Kùzu support IN $list?"""
    result = kuzu_db.execute(
        "MATCH (m:Mem) WHERE m.id IN $ids RETURN m.id",
        parameters={"ids": ["m1", "m2"]},
    )
    rows = _fetch_all(result)
    assert len(rows) == 2, f"IN $list failed: got {len(rows)} rows, expected 2"


def test_unwind_list_of_dicts(kuzu_db):
    """Does Kùzu support UNWIND $list AS item where item is a dict?"""
    result = kuzu_db.execute(
        "UNWIND $items AS item MATCH (m:Mem {id: item.id}) RETURN m.id",
        parameters={"items": [{"id": "m1"}, {"id": "m2"}]},
    )
    rows = _fetch_all(result)
    assert len(rows) == 2, f"UNWIND list-of-dicts failed: got {len(rows)} rows, expected 2"


def test_in_with_join(kuzu_db):
    """Does WHERE m.id IN $ids AND k.word IN $kws work in a MATCH/join?"""
    result = kuzu_db.execute(
        "MATCH (m:Mem)-[hk:HAS_KW]->(k:Kw) "
        "WHERE m.id IN $mids AND k.word IN $kws "
        "RETURN m.id AS memory_id, SUM(hk.tfidf) AS tfidf_sum",
        parameters={"mids": ["m1"], "kws": ["python", "async"]},
    )
    rows = _fetch_all(result)
    assert len(rows) > 0, "IN $list join query returned no rows"
    assert rows[0]["tfidf_sum"] > 0, "tfidf_sum should be > 0"
