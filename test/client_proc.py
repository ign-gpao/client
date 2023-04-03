import psutil
import signal
import subprocess
import pytest
import time


def kill_child_processes(parent_pid, sig=signal.SIGTERM):
    try:
        parent = psutil.Process(parent_pid)
    except psutil.NoSuchProcess:
        return
    children = parent.children(recursive=True)

    for process in children:
        process.send_signal(sig)


class ClientProc(object):
    
    def __init__(self, name: str):
        self.name = name
    
    def start(self, option: str=""):

        suffix_option = ""
        if (self.name != ""):
            suffix_option = f" -s _{self.name}"

        cmd = f"python -m client.client {suffix_option} -n 1 {option}"
        print("Start client with command: " + cmd)
        self.proc = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if self.is_terminated():
            # fail showing output
            output = ''.join(str(x) for x in self.stdout.readlines())
            pytest.fail("client doest NOT start, stdout is: " + output)

        # sleep to be sure the client threads are started
        time.sleep(0.5)
        return self


    def stop(self):
        kill_child_processes(self.proc.pid, signal.SIGINT)
        time.sleep(0.1)
        return self


    def stop_hard(self):
        kill_child_processes(self.proc.pid, signal.SIGTERM)
        time.sleep(0.1)
        return self


    def print_output(self):
        print(f"Client {self.name} output:")
        for line in self.proc.stdout.readlines():
            print(line)


    def is_terminated(self):
        return self.proc.poll() is not None


    def assert_is_running(self):
        assert not self.is_terminated()
        return self


    def assert_exit(self, expected_return_code: int=0):
        
        assert self.is_terminated()

        actual_return_code = self.proc.poll()
        if actual_return_code != expected_return_code:
            self.print_output()
            pytest.fail(f"Client {self.name} return code is {str(actual_return_code)} and should be {expected_return_code}")
