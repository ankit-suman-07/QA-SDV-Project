"""Line-flushed JSONL output.

Each observation is flushed as soon as it is written, so a reader such as
`tail -f vehicle-001.jsonl | observation_publisher` sees it during the run,
not when the file is closed.
"""


class LineSink:
    def __init__(self, path):
        self._handle = open(path, "w", encoding="utf-8")

    def write(self, line):
        if not line.endswith("\n") or "\n" in line[:-1]:
            raise ValueError("write exactly one newline-terminated line")
        self._handle.write(line)
        self._handle.flush()

    def close(self):
        self._handle.close()
