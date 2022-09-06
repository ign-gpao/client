import random
import subprocess
import time
import tempfile
import shlex
import platform
import ctypes
import requests
import os
import logging
import signal
import multiprocessing

# espace libre minimal en Go sur un dossier de travail pour accepter un job
MIN_AVAILABLE_SPACE = 5
# duree minimale en s entre deux requetes de mise a jour du log
MIN_FLUSH_RATE = 5

URL_API = (
    "http://"
    + os.getenv("URL_API", "localhost")
    + ":"
    + os.getenv("API_PORT", "8080")
    + "/api/"
)

def send_request(url, mode, json=None, str_thread_id=None):
    """ Fonction executant les requetes http """
    success = False
    logging.debug("%s : %s : %s%s", str_thread_id, mode, URL_API, url)
    while not success:
        try:
            if mode == "GET":
                req = requests.get(URL_API+url)
                req.raise_for_status()
                return req
            if mode == "PUT":
                req = requests.put(URL_API+url)
                req.raise_for_status()
                return req
            if mode == "POST":
                req = requests.post(URL_API+url, json=json)
                req.raise_for_status()
                return req
        except requests.exceptions.Timeout:
            logging.error("%s : timeout sur l'url : %s", str_thread_id, url)
            time.sleep(1)
        except requests.exceptions.TooManyRedirects:
            logging.error("%s : timeout sur l'url : %s", str_thread_id, url)
            time.sleep(1)
        except requests.exceptions.RequestException as exception:
            logging.error("%s : Erreur sur la requete : %s",
                          str_thread_id, url)
            logging.error("%s : Erreur %s", str_thread_id, exception)
            time.sleep(1)


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


def read_stdout_process(proc, id_job, str_thread_id, command):
    """ Lecture de la sortie console """
    last_flush = time.time()
    command_str = "Commande : "+str(command)+"\n\n"

    url_tmp = "job/" + str(id_job) + "/appendLog"

    send_request(url_tmp,
                 "POST",
                 json={"log": command_str},
                 str_thread_id=str_thread_id)

    realtime_output = ""

    while True:
        realtime_output += proc.stdout.readline()
        realtime_output = realtime_output.replace('\x00','')

        if proc.poll() is not None:
            # entre temps, des nouveaux messages sont peut-etre arrives
            for line in proc.stdout.readlines():
                realtime_output += line
                realtime_output = realtime_output.replace('\x00','')

            if realtime_output:
                url_tmp = "job/" + str(id_job) + "/appendLog"

                send_request(url_tmp,
                             "POST",
                             json={"log": realtime_output},
                             str_thread_id=str_thread_id)
            break

        if realtime_output:
            if (time.time() - last_flush) < MIN_FLUSH_RATE:
                time.sleep(MIN_FLUSH_RATE-(time.time() - last_flush))

            url_tmp = "job/" + str(id_job) + "/appendLog"

            send_request(url_tmp,
                         "POST",
                         json={"log": realtime_output},
                         str_thread_id=str_thread_id)

            realtime_output = ""
            last_flush = time.time()


def launch_command(job, str_thread_id, shell, working_dir):
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
            command = shlex.split(command, posix=False)
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
            read_stdout_process(proc, id_job, str_thread_id, command)
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


def process(parameters):
    """ Traitement pour un thread """
    hostname = parameters[0]
    str_thread_id = "[" + str(parameters[1]) + "]"
    tags = parameters[2]
    mode_exec_and_quit = parameters[3]
    id_session = -1
    # AB : Il faut passer shell=True sous windows
    # pour que les commandes systemes soient reconnues
    shell = platform.system() == "Windows"
    
    try:
        # On cree un dossier temporaire dans le dossier
        # courant qui devient le dossier d'execution
        with tempfile.TemporaryDirectory(dir=".") as working_dir:

            url = "session?host=" + hostname
            if tags:
                url += str(id_session) + "&tags=" + tags

            req = send_request(url, "PUT", str_thread_id=str_thread_id)

            id_session = req.json()[0]["id"]
            logging.info("%s : working dir (%s) id_session (%s)",
                         str_thread_id, working_dir, id_session)

            if mode_exec_and_quit:
                logging.info("%s : Ce thread devient actif", str_thread_id)
                host = hostname
                # ajout de -1 au nom du host quand c'est un client avec tag
                if tags:
                    host += "-1"
                send_request("node/setNbActive?host=" + host + "&limit=10", "POST", str_thread_id=str_thread_id)

            while True:
                # on verifie l'espace disponible dans le dossier de travail
                free_gb = get_free_space_gb(working_dir)
                req = None
                if free_gb < MIN_AVAILABLE_SPACE:
                    logging.warning(
                        "Espace disque insuffisant : %s/%s",
                        free_gb,
                        MIN_AVAILABLE_SPACE
                        )
                else:
                    url_tmp = "job/ready?id_session=" + str(id_session)
                    req = send_request(url_tmp,
                                       "GET",
                                       str_thread_id=str_thread_id)
                if req and req.json():
                    (
                        id_job,
                        return_code,
                        status,
                        error_message,
                    ) = launch_command(
                        req.json()[0], str_thread_id, shell, working_dir
                    )

                    logging.info("%s : Maj du job: %s, code_retour: %s, "
                                 "status : %s, error : %s",
                                 str_thread_id,
                                 id_job, return_code,
                                 status,
                                 error_message)

                    url_tmp = ("job?id=" + str(id_job) +
                               "&status=" + str(status) +
                               "&returnCode=" + str(return_code))

                    req = send_request(url_tmp,
                                       "POST",
                                       json={"log": error_message},
                                       str_thread_id=str_thread_id)

                    if req.status_code != 200:
                        logging.error("%s : Mauvais statut code : %s, %s",
                                      str_thread_id,
                                      req.status_code,
                                      req.content)
                else:
                    if mode_exec_and_quit:
                        logging.info("%s : Mode test, et plus de job à faire => sortie", str_thread_id)
                        raise KeyboardInterrupt
                
                # sleep
                if not mode_exec_and_quit:
                    time.sleep(random.randrange(10))
    except KeyboardInterrupt:
        logging.info("%s : on demande au process de s'arreter", str_thread_id)

        req = send_request("session/close?id=" + str(id_session),
                           "POST",
                           str_thread_id=str_thread_id)

    logging.info("%s : Fin du thread", str_thread_id)


def exec_multiprocess(hostname, nb_process, tags, mode_exec_and_quit):

    with multiprocessing.Pool(nb_process) as POOL:
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        parameters = []
        for id_thread in range(nb_process):
            parameters.append((hostname, id_thread, tags, mode_exec_and_quit))

        try:
            POOL.map(process, parameters)

        except KeyboardInterrupt:
            logging.info("on demande au pool de s'arreter")
            POOL.terminate()
        else:
            logging.info("Normal termination")
            POOL.close()
        POOL.join()
