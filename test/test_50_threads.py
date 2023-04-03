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

    FILENAME = "test_50_threads.json"

    jobs = []
    for i in range(50):
    # create jobs
        jobs.append(Job(f"{i}/50 - test_50_thread_loop2_should_last_30_sec", "python -u ../test/loop2.py", tags=[TAG]))

    project1 = Project("test_client_50_threads_" + socket.gethostname(), jobs)
 
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

    worker.exec_multiprocess(50, parameters)