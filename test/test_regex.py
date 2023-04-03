import shutil
import os
from client import worker
import glob

def setup_module(module):
    for file in glob.glob("tmp*"):
        shutil.rmtree(file)

    os.mkdir("tmp_Alicea4xxd0a8")
    os.mkdir("tmp_Alicefysbtmwl")
    os.mkdir("tmp5kuibbir")


def test_list_tmp_folder_suffix():
    assert len(worker.list_tmp_folder("_Alice")) == 2


def test_list_tmp_folder_no_suffix():
    assert len(worker.list_tmp_folder("")) == 1