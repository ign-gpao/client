from client import worker

import os
import requests

from gpao.builder import Builder
from gpao.project import Project
from gpao.job import Job
import socket

# Use a unique tag, to be shure that the job is done by this client.
TAG = "client_gpao_test_unit_on_" + socket.gethostname()

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
    job = Job("test_loop_should_last_lest_than_1_sec", "python -u ../test/loop.py", tags=[TAG])
    job2 = Job("test_loop2_should_last_30_sec", "python -u ../test/loop2.py", tags=[TAG])
    job3 = Job("test_loop3_should_last_30_sec", "python -u ../test/loop3.py", tags=[TAG])
    job4 = Job("test_loop4_should_print_lines_last_30_sec", "python -u ../test/loop4.py", tags=[TAG])

    project1 = Project("test_client_print_loop_" + socket.gethostname(), [job, job2, job3, job4])
 
    builder = Builder([project1])
    builder.save_as_json(FILENAME)
    assert os.path.isfile(FILENAME)

    response = send_project(FILENAME)
    assert response.status_code == 200


def test_3_execute_gpao_client_multithreaded():

    parameters = {
        'url_api': worker.URL_API,
        'hostname': socket.gethostname(),
        'tags': TAG,
        'autostart': '50',
        'mode_exec_and_quit': True,
        'suffix': ""
    }

    worker.exec_multiprocess(1, parameters)