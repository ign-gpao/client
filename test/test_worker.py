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

    FILENAME = "test_project1.json"

    # create jobs
    job1 = Job("job1", "echo simple job 1")
    job2 = Job("job2", "echo simple job 2")

    job3 = Job("job3", "echo job3 should be done after job1 and job2")
    job3.add_dependency(job1)
    job3.add_dependency(job2)

    project1 = Project("project1", [job1, job2, job3])
 
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
        'autostart': '3',
        'mode_exec_and_quit': True,
        'suffix': ""
    }


    worker.exec_multiprocess(3, parameters)
