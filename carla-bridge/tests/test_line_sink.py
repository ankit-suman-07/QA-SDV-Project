"""Observations are readable line by line while the run is still writing."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from line_sink import LineSink  # noqa: E402


def test_each_line_is_visible_to_a_reader_before_close(tmp_path):
    path = tmp_path / "vehicle-001.jsonl"
    sink = LineSink(path)
    with open(path) as reader:
        sink.write('{"a":1}\n')
        assert reader.readline() == '{"a":1}\n'
        sink.write('{"a":2}\n')
        assert reader.readline() == '{"a":2}\n'
    sink.close()


def test_rejects_a_write_that_is_not_exactly_one_line(tmp_path):
    import pytest
    sink = LineSink(tmp_path / "x.jsonl")
    for bad in ('{"a":1}', '{"a":1}\n{"b":2}\n'):
        with pytest.raises(ValueError):
            sink.write(bad)
    sink.close()
    assert (tmp_path / "x.jsonl").read_text() == ""
