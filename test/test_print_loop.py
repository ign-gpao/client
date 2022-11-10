from client import worker

import os
import pytest
import requests

from gpao.builder import Builder
from gpao.project import Project
from gpao.job import Job


def send_project(filename: str):
    headers = {
        'Content-type': 'application/json',
    }
    data = open(filename, 'rb')
    response = requests.put(worker.URL_API+ "project", headers=headers, data=data)
    return response


def test_1_create_gpao():

    FILENAME = "test_print_loop.json"

    # create jobs
    job = Job("test_loop_should_last_lest_than_1_sec", "python -u ../test/loop.py")
    job2 = Job("test_loop2_should_last_30_sec", "python -u ../test/loop2.py")
    job3 = Job("test_loop3_should_last_30_sec", "python -u ../test/loop3.py")

    project1 = Project("test_client_print_loop", [job, job2, job3])
 
    builder = Builder([project1])
    builder.save_as_json(FILENAME)
    assert os.path.isfile(FILENAME)

    response = send_project(FILENAME)
    assert response.status_code == 200


def test_3_execute_gpao_client_multithreaded():

    worker.exec_multiprocess(worker.URL_API, "test_client", 1, "", True)