import os
import tempfile

from src.agent.tools.file_tool import read_file, write_file


def test_file_read_write_cycle():
    with tempfile.TemporaryDirectory() as td:
        # set AGENT_BASE_DIR for the test by writing to config via env
        os.environ["AGENT_BASE_DIR"] = td
        # write
        ok, out = write_file("sub/test.txt", "hello world")
        assert ok
        ok, content = read_file("sub/test.txt")
        assert ok and content == "hello world"
