"""
Client pour la GPAO
Permet de lancer un thread par coeur
"""
# !/usr/bin/python
import sys
import multiprocessing

import argparse
import logging
import socket
from client import worker

NB_PROCESS = multiprocessing.cpu_count()

HOSTNAME = socket.gethostname()

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
        logging.FileHandler("client.log"),
        logging.StreamHandler()
    ],
    format='%(asctime)s %(levelname)-5s %(message)s',
    level=logging.DEBUG if ARGS.verbose else logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')



if __name__ == "__main__":
    logging.info("Demarrage du client GPAO")
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

    REQ_NB_SESSIONS = worker.send_request("nodes", "GET")

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
                      "ouvertes avec ce nom de machine.")
        logging.error("Pour lancer plusieurs client sur une meme machine,"
                      " utiliser un suffixe "
                      "(ex: python client.py -s _MonSuffixe).")
        sys.exit(1)

    worker.exec_multiprocess(HOSTNAME, NB_PROCESS, ARGS.tags, False)

    logging.info("Fin du client GPAO")
