from __future__ import annotations
from enum import Enum
from io import BytesIO
from queue import Queue
import signal
import psutil
import subprocess as subp
import sys
import threading as th

import time
from typing import Any
import os

class PipeType(Enum):
    OUT = 0
    ERR = 1
    ALL = 2
    IN = 3

class CLITool:
    "Shell command."
    def __init__(self, name:str) -> None:
        "A class that represents a shell command."
        self.name = name
        self.process:subp.Popen = None
        self.pipe_in:bytes | CLITool = None
        self.args = []
        self.thread = th.Thread(target=lambda:self._run())
        self._stdout_thread = th.Thread(target=lambda:self._stdout_reader())
        self._stderr_thread = th.Thread(target=lambda:self._stderr_reader())
        
        self._stderr:bytes = None
        self._stdout:bytes = None
        self._all:bytes = None

        self._stderr_buffer:bytes = b''
        self._stdout_buffer:bytes = b''
        self._all_buffer:bytes = b''


        self._all_queue = Queue()
        self._stdout_queue = Queue()
        self._stderr_queue = Queue()
        self._stdin_queue = Queue()

        self.pipe_in_type = PipeType.OUT
        self.concurrent = False
        self.has_run = False

    def __call__(self, *args: Any) -> CLITool:
        self.args = [self.name, *[str(arg) for arg in args]]
        return self

    
    def _run(self):
        "Run the command."
        self.process = subp.Popen(" ".join(self.args), shell=True,
            stdout=subp.PIPE, stderr=subp.PIPE, stdin=subp.PIPE)
        
        self._stdout_thread.start()
        self._stderr_thread.start()

        pipe_in = b''
        
        if isinstance(self.pipe_in, CLITool):
            if not self.pipe_in.has_run:
                self.pipe_in.run()
            if self.pipe_in_type == PipeType.ERR:
                pipe_in = self.pipe_in.stderr
            elif self.pipe_in_type == PipeType.OUT:
                pipe_in = self.pipe_in.stdout
            elif self.pipe_in_type == PipeType.ALL:
                pipe_in = self.pipe_in.all
        else:
            pipe_in = self.pipe_in
        
        if pipe_in != None:
            self.process.stdin.writelines(pipe_in.splitlines())

        # self._stdout, self._stderr = self.process.communicate()
        self._kill_stream_threads()
        
        if len(self._stdout) < len(self._stdout_buffer) if self._stdout != None else True:
            self._stdout = self._stdout_buffer
        if len(self._stderr) < len(self._stderr_buffer) if self._stderr != None else True:
            self._stdout = self._stdout_buffer
        self._all = self._all_buffer
        
    
        return self 
        
    def _stdout_reader(self):
        while self.process.poll() == None:
            try:
                for data in self.process.stdout.readlines():
                    self._stdout_queue.put(data, False)
                    self._stdout_buffer += data
                    self._all_queue.put(data, False)
                    self._all_buffer += data
            except:
                pass
                

    def _stderr_reader(self):
        while self.process.poll() == None:
            try:
                for data in self.process.stderr.readlines():
                    self._stderr_queue.put(data, False)
                    self._stderr_buffer += data
                    self._all_queue.put(data, False)
                    self._all_buffer += data
            except:
                pass
                
        
                
    
    def _kill_stream_threads(self):
        if self._stdout_thread.is_alive():
            self._stdout_thread.join()
        if self._stderr_thread.is_alive():
            self._stderr_thread.join()
        
        
        
    
    def run(self):
        "Runs the process."
        self.has_run = True
        if self.concurrent:
            self._run_concurrent()
            while self.process == None:
                pass
            return self
        else:
            self._run()
            self.finish()
            return self
        
    
    def _run_concurrent(self):
        "Runs process on a separate thread."
        self.thread.start()
        return self
    
    def __invert__(self):
        "`&`\n\nRuns process on a separate thread."
        self.concurrent = True
        return self

    def __or__(self, other:CLITool | Any):
        "`|`\n\nPipe stdout into right hand side as a string."
        if isinstance(other, CLITool):
            other.pipe_in = self
            return other
        else:
            raise TypeError("Cant stdout pipe Shell command into type other than another shell command")
    
    def __ror__(self, other:Any):
        "`|`\n\nPipe python type into right hand side as a string."
        self.pipe_in = str(other).encode()
        return self
    
    def __matmul__(self, other:CLITool):
        "`2> >(process)`\n\nPipe stderr into right hand side as a string."
        if isinstance(other, CLITool):
            other.pipe_in = self
            other.pipe_in_type = PipeType.ERR
            return other
        else:
            raise TypeError("Cant stderr pipe Shell command into type other than another shell command")
        
    def __mod__(self, other:CLITool):
        "`|&`\n\nPipe stderr and stdout into right hand side as a string."
        if isinstance(other, CLITool):
            other.pipe_in = self
            other.pipe_in_type = PipeType.ALL
            return other
        else:
            raise TypeError("Cant stderr pipe Shell command into type other than another shell command")
        
    def kill(self):
        "Kills the process."
        if self.running:
            os.kill(self.pid, signal.SIGTERM)
        else:
            raise RuntimeError(f"Tried to kill process that doesnt exist with pid:({self.pid}).")
        return self
    
    def __iter__(self):
        return self


    def __next__(self):
        
        if self._stdout_queue.empty() and self._stderr_queue.empty():
            raise StopIteration()
        
        return self.next_stream_line()
        
        
    def next_stream_line(self):
        "Grabs next `(stdout, stderr)` in the stream captured durring runtime.\n\n~~NOTE~~: If the stdout is buffered, it will not capture the stdout and stderr until the process is complete."
        stdout:bytes | None = None
        if not self._stdout_queue.empty():
            stdout = self._stdout_queue.get(True)

        stderr:bytes | None = None
        if not self._stderr_queue.empty():
            stderr = self._stderr_queue.get(True)
        
        
        return (stdout, stderr)

    @property
    def running(self):
        "Returns True if the process is running, False if not."
        return self.process.poll() == None if self.process != None else False
    
    @property
    def stream_empty(self):
        "Returns True if the stdout and stderr streams are empty, False if not."
        
        return self._stdout_queue.empty() and self._stderr_queue.empty()
    
    @property
    def return_code(self):
        if not self.running and self.process != None:
            return self.process.returncode
        else:
            return None

    @property
    def pid(self):
        if self.process != None:
            return self.process.pid
        return None
    
    def finish(self):
        "Blocks code untill process is finished.  Basically the same as `.join()`ing the thread."
        if self.thread.is_alive():
            self._kill_stream_threads()
            self.thread.join()
        
        # else:
        #     raise RuntimeError("Concurrent process is not running.")
    
    @property
    def stdout(self):
        if self._stdout != None:
            return self._stdout
        self.finish()
        return self._stdout
    
    @property
    def stderr(self):
        if self._stderr != None:
            return self._stderr
        self.finish()
        return self._stderr
    
    @property
    def all(self):
        if self._all != None:
            return self._all
        self.finish()
        return self._all

class Shell:
    def __getattribute__(self, name: str) -> CLITool:
        "Shell command."
        return CLITool(name)
    def __getitem__(self, name: str) -> CLITool:
        "Shell command."
        return CLITool(name)
    def __getattr__(self, name: str) -> CLITool:
        "Shell command."
        return CLITool(name)
    
SHELL = Shell()

if __name__ == "__main__":
    
    process = (SHELL.findstr("/s", "/c:Tool", "C:/Users/William/Documents/Programming Repos/*.py") | SHELL.findstr("/s", "/c:SHELL"))
    #process = SHELL.python("-u", "./test/t1.py")
    process.run()
    while process.running or not process.stream_empty:
        out, err = process.next_stream_line()
        #print("hello")

        if out:
            sys.stdout.write(f"out:\n{out.decode()}")

        if err:
            sys.stdout.write(f"err:\n{err.decode()}")
        

    sys.stdout.write(process.all.decode())