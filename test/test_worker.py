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


@pytest.mark.skip(reason="skip exec gpao mono threaded")
def test_2_execute_gpao_client():

    worker.exec_multiprocess("test_client", 1, "", True)


def test_3_execute_gpao_client_multithreaded():

    worker.exec_multiprocess(worker.URL_API, "test_client", 3, "", True)
