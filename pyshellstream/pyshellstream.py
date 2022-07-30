import sys
from subprocess import PIPE, Popen
from threading import Thread
from queue import Queue, Empty
from typing import List, Union, Tuple
import re


class ShellStreamProcess:
    def __init__(self, popen_process: Popen, stdout_queue: Queue):
        self.process = popen_process
        self.stdout_queue = stdout_queue

    def process_is_running(self):
        return self.process.poll() is None

    def writelines(self, line: Union[List[str], List[bytes]]):
        self.process.stdin.writelines(line)

    def write(self, string: Union[str, bytes]):
        self.process.stdin.write(string)

    def readline(self, timeout=None) -> Tuple[str, bool]:
        try:
            next_line = self.stdout_queue.get(True, timeout)
            return next_line, False
        except Empty:
            return "", True

    def readlines(self) -> str:
        while self.process_is_running() or (not self.process_is_running() and not self.stdout_queue.empty()):
            next_line, timed_out = self.readline(timeout=0)
            if not timed_out:
                yield next_line

    def has_next_line(self):
        return not self.stdout_queue.empty()

    def return_if_partial_line_match(self, matcher: Union[str, re.Pattern], include_match=False) -> str:
        pass

    def return_lines_after_match(self, matcher: Union[str, re.Pattern], include_match=False) -> str:
        if isinstance(matcher, str):
            match_evaluator = lambda x: matcher == x
        elif isinstance(matcher, re.Pattern):
            match_evaluator = lambda x: matcher.match(x)
        else:
            raise TypeError(f"Unexpected type for matcher. Expected type {[str, re.Pattern]} but got {[type(matcher)]}")

        has_matched = False
        for next_line in self.readlines():
            if not has_matched and match_evaluator(next_line):
                has_matched = True
                if include_match:
                    yield next_line
            elif has_matched:
                yield next_line


def shell_stream(args: List[str], line_buffered: bool = True) -> ShellStreamProcess:
    on_posix = 'posix' in sys.builtin_module_names
    popen_process = Popen(
        args, stdout=PIPE, stdin=PIPE, stderr=PIPE,
        bufsize=1 if line_buffered else 0, close_fds=on_posix,
        text=True
    )
    stdout_queue = Queue()
    subprocess_thread = Thread(target=enqueue_output, args=(popen_process, stdout_queue), daemon=True)
    subprocess_thread.start()
    return ShellStreamProcess(popen_process, stdout_queue)


def enqueue_output(popen_process: Popen, queue: Queue):
    for process_next_line in popen_process.stdout:
        queue.put(process_next_line)
    popen_process.stdout.close()


process = shell_stream(["python3", "-u", "runner.py"])


for index, line in enumerate(process.return_lines_after_match(re.compile(r"Two lines.*"), include_match=True)):
    print(f"Got line: {line}")
    if index == 1:
        process.writelines(["Test input\n"])


# process.return_if_line_matches("", include_non_matching=True)
#
# process.read
# process.readline()
# process.has_next_line()
# process.return_lines_after_match(re.compile(""), include_match=False)
# process.write()
# process.write_lines("Test")



