from client import worker

import time
import glob
from client_proc import ClientProc


def test_client_normal_start_stop():
    alice = ClientProc("Alice").start("-c")
    alice.stop().assert_exit(0)


def test_client_with_existing_session_exit1():
    ClientProc("Alice").start("-c").stop_hard()
    ClientProc("Alice").start().assert_exit(1)


def test_client_with_existing_session_start_with_option_clean():
    alice = ClientProc("Alice").start("-c").stop_hard()
    
    alice = ClientProc("Alice").start("-c").assert_is_running()
    alice.stop().assert_exit(0)

    assert len(glob.glob("tmp_Alice*")) == 0


def test_2_client_cleaning():
    alice = ClientProc("Alice").start("--clean")
    bob = ClientProc("Bob").start("--clean")

    # issue with the folder comes when client scan disk space in the specific folder
    time.sleep(30)

    alice.stop().assert_exit()
    bob.stop().assert_exit()


def test_2_client_cleaning_and_third_without_suffix():
    alice = ClientProc("Alice").start("--clean")
    bob = ClientProc("Bob").start("--clean")
    no_name = ClientProc("").start("--clean")

    # issue with the folder comes when client scan disk space in the specific folder
    time.sleep(30)

    alice.stop().assert_exit()
    bob.stop().assert_exit()
    no_name.stop().assert_exit()
