"""
Client pour la GPAO
Permet de lancer un thread par coeur
"""
# !/usr/bin/python
import os
import sys
import stat
import multiprocessing

import argparse
import logging
import socket

import glob
import shutil

from client import worker
from . import __version__

NB_PROCESS = multiprocessing.cpu_count()

HOSTNAME = socket.gethostname()

LOG_FILENAME = "client.log"


def arg_parser():
    """ Extraction des arguments de la ligne de commande """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-n",
        "--threads",
        required=False,
        type=int,
        help="fix the number of threads \
                        (default: estimated number of cpu on the system)",
    )
    parser.add_argument(
        "-s",
        "--suffix",
        help="add a suffix on the hostname \
                        (necessary if using several \
                        client instances on a machine)",
        required=False,
        type=str,
    )
    parser.add_argument(
        "-t",
        "--tags",
        required=False,
        type=str,
        default="",
        help="comma separated list of tags",
    )
    parser.add_argument(
        "-c",
        "--clean",
        help="delete old temporary dir and \
                        close all open sessions",

        required=False,
        action="store_true",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        required=False,
        help="increase output verbosity",
        action="store_true",
    )
    return parser.parse_args()


ARGS = arg_parser()

logging.basicConfig(
    handlers=[
        logging.FileHandler(LOG_FILENAME),
        logging.StreamHandler()
    ],
    format='%(asctime)s %(levelname)-5s %(message)s',
    level=logging.DEBUG if ARGS.verbose else logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')

# AB : Ajout des droits en lecture/ecriture pour tous
# https://www.tutorialspoint.com/python/os_chmod.htm
os.chmod(LOG_FILENAME, stat.S_IRUSR |
         stat.S_IWUSR |
         stat.S_IRGRP |
         stat.S_IWGRP |
         stat.S_IROTH |
         stat.S_IWOTH)


if __name__ == "__main__":
    logging.info("Demarrage du client GPAO")
    logging.info("Version du client : %s", __version__)
    logging.info("URL_API : %s", worker.URL_API)

    logging.debug("Argument : %s", ARGS)
    if ARGS.threads:
        if ARGS.threads <= 0:
            logging.error("Le nombre de thread doit etre >0 : %s",
                          ARGS.threads)
            sys.exit(1)
        NB_PROCESS = ARGS.threads
    if ARGS.suffix:
        HOSTNAME += ARGS.suffix

    logging.info("HOSTNAME : %s", HOSTNAME)
    logging.info("NB_PROCESS : %s", NB_PROCESS)

    if ARGS.clean:
        logging.info("Appel de la fonction nettoyage")
        logging.info("  Suppression des répertoires temporaires")

        logging.info("  Nombre de répertoire à supprimer : %s",
                     len(glob.glob('tmp*')))

        for file in glob.glob('tmp*'):
            shutil.rmtree(file)

        logging.info("  Suppression des sessions obsolètes")
        REQ_NB_SESSIONS_CLOSE = worker.send_request(
            worker.URL_API + "sessions/close?hostname=" + str(HOSTNAME),
            "POST"
            )
        logging.info("  Nombre de sessions fermées : %s",
                     REQ_NB_SESSIONS_CLOSE.json()[0]["nb_sessions"])

    REQ_NB_SESSIONS = worker.send_request(worker.URL_API + "nodes", "GET")

    NODES = REQ_NB_SESSIONS.json()
    NB_SESSION = 0
    for node in NODES:
        if node["host"] == HOSTNAME:
            # attention, les donnees sont en string
            # a corriger dans l'API
            NB_SESSION = (
                int(node["active"]) + int(node["idle"]) + int(node["running"])
            )
    if NB_SESSION > 0:
        logging.error("Erreur: il y a deja des sessions "
                      "ouvertes avec ce nom de machine."
                      "Pour lancer plusieurs client sur une même machine, "
                      "utilisez un suffixe "
                      "(ex: python -m client.client -s _MonSuffixe)."
                      "Sinon vous pouvez utiliser l'option --clean "
                      "pour purger les sessions non fermées")
        sys.exit(1)

    worker.exec_multiprocess(
        worker.URL_API,
        HOSTNAME,
        NB_PROCESS,
        ARGS.tags,
        False
    )

    logging.info("Fin du client GPAO")
