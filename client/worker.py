"""
Client pour la GPAO
Permet de lancer un thread par coeur
"""
# !/usr/bin/python
import random
import subprocess
import time
import tempfile
import shlex
import platform
import ctypes
import os
import logging
import signal
import multiprocessing
from functools import partial
import re
import requests

# espace libre minimal en Go sur un dossier de travail pour accepter un job
MIN_AVAILABLE_SPACE = int(os.getenv("GPAO_MIN_AVAILABLE_SPACE", "5"))

# duree minimale en s entre deux requetes de mise a jour du log
MIN_FLUSH_RATE = 5

GPAO_API_URL = (
    os.getenv("GPAO_API_PROTOCOL", "http") + "://"
    + os.getenv("GPAO_API_URL", "localhost")
    + ":"
    + os.getenv("GPAO_API_PORT", "8080")
    + "/api/"
)


def list_tmp_folder(suffix: str):
    """List tmp folder on the disk.
    Parameter suffix can be empty string, or any suffix."""
    regex = "tmp" + suffix + ".{8}$"
    return [f for f in os.listdir('.') if re.match(regex, f)]


def build_url_api(hostname: str, port="8080"):
    """construit l'url"""
    return f"http://{hostname}:{port}/api/"


def send_request(url, mode, json=None, str_thread_id=None):
    """ Fonction executant les requetes http """
    logging.debug("%s : %s : %s", str_thread_id, mode, url)
    while True:
        try:
            req = ""
            if mode == "GET":
                req = requests.get(url, timeout=60)
                req.raise_for_status()
            if mode == "PUT":
                req = requests.put(url, timeout=60)
                req.raise_for_status()
            if mode == "POST":
                req = requests.post(url, json=json, timeout=60)
                req.raise_for_status()
            return req

        except requests.exceptions.Timeout:
            logging.error("%s : Timeout Error sur l'url : %s",
                          str_thread_id, url)
            time.sleep(1)
        except requests.exceptions.TooManyRedirects:
            logging.error("%s : Too many redirect Error sur l'url : %s",
                          str_thread_id, url)
            time.sleep(1)
        except requests.exceptions.ConnectionError:
            logging.error("%s : Connection Error sur l'url : %s",
                          str_thread_id, url)
            time.sleep(1)
        except requests.exceptions.HTTPError:
            logging.error("%s : HTTP Error sur l'url : %s, code = %s",
                          str_thread_id, url,
                          req.status_code)
            if req.status_code == 404:
                logging.info("Le job n'existe pas dans la base, "
                             "on passe à la suite")
                return req
            time.sleep(1)
        except requests.exceptions.RequestException as exception:
            logging.error("%s : Erreur sur la requete : %s",
                          str_thread_id, url)
            logging.error("%s : Erreur %s", str_thread_id, exception)
            time.sleep(1)
    return None


def get_free_space_gb(dirname):
    """ Fonction renvoyant l'espace disque disponible """
    space_available = 0
    if platform.system() == "Windows":
        free_bytes = ctypes.c_ulonglong(0)
        ctypes.windll.kernel32.GetDiskFreeSpaceExW(
            ctypes.c_wchar_p(dirname), None, None, ctypes.pointer(free_bytes)
        )
        space_available = free_bytes.value / 1024 / 1024 / 1024
    else:
        stat = os.statvfs(dirname)
        space_available = stat.f_bavail * stat.f_frsize / 1024 / 1024 / 1024

    return space_available


def read_stdout_process(url_api: str,
                        proc: subprocess.Popen,
                        id_job,
                        str_thread_id,
                        command):
    """ Lecture de la sortie console """
    last_flush = time.time()
    command_str = "Commande : "+str(command)+"\n\n"

    url_tmp = "job/" + str(id_job) + "/appendLog"

    send_request(url_api + url_tmp,
                 "POST",
                 json={"log": command_str},
                 str_thread_id=str_thread_id)

    realtime_output = ""

    while True:

        # lit toutes les lignes
        i = 0
        while True:
            i = i + 1
            line = proc.stdout.readline()
            if line:
                realtime_output += line
            else:
                break

            # regulièrement, on sort de la boucle pour envoyer les résultats
            if (time.time() - last_flush) > MIN_FLUSH_RATE:
                break

        realtime_output = realtime_output.replace('\x00', '')

        if proc.poll() is not None:
            # entre temps, des nouveaux messages sont peut-etre arrives
            for line in proc.stdout.readlines():
                realtime_output += line
                realtime_output = realtime_output.replace('\x00', '')

            if realtime_output:
                url_tmp = "job/" + str(id_job) + "/appendLog"

                send_request(url_api + url_tmp,
                             "POST",
                             json={"log": realtime_output},
                             str_thread_id=str_thread_id)
            break

        if realtime_output:

            url_tmp = "job/" + str(id_job) + "/appendLog"

            send_request(url_api + url_tmp,
                         "POST",
                         json={"log": realtime_output},
                         str_thread_id=str_thread_id)

            realtime_output = ""
            last_flush = time.time()


def launch_command(url_api: str, job, str_thread_id, shell, working_dir):
    """ Lancement d'une ligne de commande """
    id_job = job["id"]
    command = job["command"]

    command = os.path.expandvars(command)

    logging.info("%s : L'id du job %s est disponible. "
                 "Execution de la commande [%s]",
                 str_thread_id, id_job, command)
    return_code = None
    error_message = ""
    try:
        if not shell:
            command = shlex.split(command, posix=True)
        with subprocess.Popen(
            command,
            shell=shell,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf8",
            errors="replace",
            universal_newlines=True,
            cwd=working_dir,
        ) as proc:
            read_stdout_process(url_api, proc, id_job, str_thread_id, command)
            return_code = proc.poll()
            status = "done"
    except subprocess.CalledProcessError as ex:
        status = "failed"
        error_message += str(ex)
    except OSError as ex:
        status = "failed"
        error_message += str(ex)
    if return_code != 0:
        status = "failed"
        if return_code is None:
            return_code = -1
    if error_message:
        logging.error("Erreur : %s", error_message)
    error_message += "FIN"
    return id_job, return_code, status, error_message


def is_enought_free_space_on_disk(working_dir):
    """return True is there is space on the disk"""
    free_gb = get_free_space_gb(working_dir)
    if free_gb < MIN_AVAILABLE_SPACE:
        logging.warning(
            "Espace disque insuffisant : %s/%s",
            free_gb,
            MIN_AVAILABLE_SPACE
            )
        return False
    return True


def custom_sleep(mode_test: bool):
    """ Pause, plus courte pour les tests """
    if mode_test:
        # test should be fast
        time.sleep(random.randrange(2, 5))
    else:
        time.sleep(random.randrange(20, 30))


def insert_session(hostname, tags, url_api, str_thread_id):
    """ Insertion d'une nouvelle session """

    url = "session?host=" + hostname
    if tags is not None:
        url += "&tags=" + tags

    req = send_request(url_api + url,
                       "PUT",
                       str_thread_id=str_thread_id)

    return req.json()[0]["id"]


def refresh_session(hostname,
                    tags,
                    url_api,
                    str_thread_id,
                    id_session):
    """ Fonction qui vérifie que la session est présente
        et l'enregistre si nécesssaire """

    url = "sessions/" + hostname
    req = send_request(url_api+url,
                       "GET",
                       str_thread_id=str_thread_id)

    for row in req.json():
        if row['id'] == id_session:
            return id_session

    return insert_session(hostname, tags, url_api, str_thread_id)


def process(parameters, id_thread):
    """ Traitement pour un thread """
    url_api = parameters["url_api"]
    str_thread_id = "[" + str(id_thread) + "]"
    id_session = -1
    # AB : Il faut passer shell=True sous windows
    # pour que les commandes systemes soient reconnues
    shell = platform.system() == "Windows"

    try_before_exiting = 2
    try:
        # On cree un dossier temporaire dans le dossier
        # courant qui devient le dossier d'execution
        with tempfile.TemporaryDirectory(dir=".",
                                         prefix="tmp" + parameters["suffix"]
                                         ) as working_dir:

            id_session = insert_session(parameters["hostname"],
                                        parameters["tags"],
                                        url_api,
                                        str_thread_id)

            logging.info("%s : working dir (%s) id_session (%s)",
                         str_thread_id, working_dir, id_session)

            if int(parameters["autostart"]) > 0:
                logging.debug("%s : Ce thread devient actif", str_thread_id)
                host = parameters["hostname"]

                send_request(url_api + "node/setNbActive?value=" +
                             parameters["autostart"],
                             "POST",
                             json={"hosts": [host]},
                             str_thread_id=str_thread_id)

            while True:
                req = None

                # on verifie que la session est toujours présente dans la base
                # et si besoin on en insére une nouvelle
                id_session = refresh_session(parameters["hostname"],
                                             parameters["tags"],
                                             url_api, str_thread_id,
                                             id_session
                                             )

                # on verifie l'espace disponible dans le dossier de travail
                # avant de chercher un nouveau job
                if is_enought_free_space_on_disk(working_dir):
                    url = "job/ready?id_session=" + str(id_session)
                    req = send_request(url_api + url,
                                       "GET",
                                       str_thread_id=str_thread_id)
                if req and req.json():
                    (
                        id_job,
                        return_code,
                        status,
                        error_message,
                    ) = launch_command(
                        url_api,
                        req.json()[0],
                        str_thread_id,
                        shell,
                        working_dir
                    )

                    logging.info("%s : Maj du job: %s, code_retour: %s, "
                                 "status : %s, error : %s",
                                 str_thread_id,
                                 id_job, return_code,
                                 status,
                                 error_message)

                    url = ("job?id=" + str(id_job) +
                           "&status=" + str(status) +
                           "&returnCode=" + str(return_code))

                    req = send_request(url_api + url,
                                       "POST",
                                       json={"log": error_message},
                                       str_thread_id=str_thread_id)

                    if req.status_code not in (200, 404):
                        logging.error("%s : Mauvais statut code : %s, %s",
                                      str_thread_id,
                                      req.status_code,
                                      req.content)
                else:
                    if parameters["mode_exec_and_quit"]:
                        if try_before_exiting <= 0:
                            logging.info("%s : Mode test, et plus de "
                                         "job à faire => sortie",
                                         str_thread_id)
                            raise KeyboardInterrupt
                        try_before_exiting = try_before_exiting - 1

                    custom_sleep(parameters["mode_exec_and_quit"])

    except KeyboardInterrupt:
        logging.info("%s : On demande au process de s'arreter", str_thread_id)

        send_request(url_api + "session/close?id=" + str(id_session),
                     "POST",
                     str_thread_id=str_thread_id)

    logging.info("%s : Fin du thread", str_thread_id)


def exec_multiprocess(nb_process, parameters):
    """ Execution du multiprocess. parameter is a dict containing:
        parameters = {
        'url_api': str,
        'hostname': str,
        'tags': "tags separated by ,",
        'autostart': "Number of threads active, as string",
        'mode_exec_and_quit': True or False,
        'suffix': empty string or any suffix
    }
    """
    if platform.system() == "Windows":
        if nb_process > 60:
            logging.info("Limite Windows: 60 threads au lieu des %s demandés",
                         nb_process)
            nb_process = 60

    with multiprocessing.Pool(nb_process) as pool:
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        func_process = partial(process, parameters)

        try:
            pool.map(func_process, range(nb_process))

        except KeyboardInterrupt:
            logging.info("On demande au pool de s'arreter")
            pool.terminate()
        else:
            pool.close()
        pool.join()
