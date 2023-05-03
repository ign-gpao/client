# Client

IGN GPAO Client est un module développée en [Python](https://www.python.org/) qui exécute des traitements (lignes de commande) en optimisant les ressources de la machine sur laquelle il est installé.

## Installation

1. Cloner le dépôt ign-gpao/client
2. Dans le répertoire du client, lancer la commande : `python3 -m client.client`

## Variables d'environnement

La configuration de variables d'environnement propres au Client est nécessaire pour son bon fonctionnement. Elles sont définies par défaut mais sont à adapter en fonction de votre installation. En voici l'inventaire :

| Variable | Obligatoire | Valeur par défaut | Commentaire |
| --- | --- | --- | --- |
| API_PROTOCOL | Non | http | Protocole utilisé par le client pour se connecter à l'API |
| URL_API  | Non |  localhost  |  Nom du serveur hébergeant l'API |
| API_PORT | Non |  8080  |  Port de l'API vu par le client  |
| GPAO_MIN_AVAILABLE_SPACE | Non | 5 (Go) | Espace disque minimal pour que le client démarre |

## Utilisation

Différents paramètres optionnels peuvent être ajoutés à la commande précédente :

| Commande | Abréviation | Description |
| --- | --- | --- |
| --help | -h | Afficher l'aide au paramétrage de la commande |
| --verbose | -v | Augmenter la verbosité des logs |
| --clean | -c | Supprimer les anciens dossiers temporaires et fermer toutes les sessions ouvertes |
| --threads THREADS | -n THREADS | Fixer le nombre de threads du client, par défaut le nombre estimé de CPU de la machine |
| --suffix SUFFIX | -s SUFFIX | Ajouter un suffixe au nom du client (nécessaire si l'on utilise plusieurs clients sur une machine), par défaut nom de la machine |
| --tags TAGS | -t TAGS | Définir les tags du client (liste de tags séparés par des virgules) |
| --autostart AUTOSTART | -a AUTOSTART | Définir le nombre de threads à activer automatiquement dès le lancement du client, par défaut 0 |

## Développement

Le code peut-être analysé avec PyLint et Flake8.

### Tests

## Licence

Ce projet est sous licence CECILL-B (voir [LICENSE.md](https://github.com/ign-gpao/.github/blob/main/LICENSE.md)).

[![IGN](https://github.com/ign-gpao/.github/blob/main/images/logo_ign.png)](https://www.ign.fr)
