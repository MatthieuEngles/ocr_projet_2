# ocr_projet_2

## Description
Le programme permet d'extraire les informations concernant les livres d'un site de vente en ligne.

## Installation de l'environnement
1. Créez un environnement virtuel.
```
python3 -m venv .ocrenv
```

2. Activez l'environnement
```
source .ocrenv/bin/activate
```
2. Installez les bibliothèques requises
```
pip install -r requirement.txt
```
## Utilisation

Lancez le programme
```
python src/scrap_book.py
```
Le programme peut prendre plusieurs arguement:
```
  -h, --help       Show this help message and exit
  -s, --src        Choisissez le site à scrapper (par defaut : http://books.toscrape.com/)
  -o, --outputdir  Choisissez en repertoire de sortie (par default : data)
  -c, --category   Choisissez la catégorie de livre à scrapper (par default : Toutes (None))
  -v, --verbose    Affiche les logs dans la console
```

Par défaut le programme va créer : 
- les répertoires:
    - data
    - data/books (où sera enregistré le fichier de résultats books.csv)
    - data/images (où seront stockées les images des couvertures)
- le fichier:
    - log.log (où sera enregistré les logs du programme)

Voici l'image finale du dossier après lancement du programme

```
project
│   README.md
│   .gitignore   
│   requirement.txt
│
└───data
│   │
│   └───books
│   |   │   books.csv  
│   |   
|   └───image
│       │   qjgdjqd.jpg
│       │   rj12jhj.jpg
│       │   ...
│   
└───src
    │   scrap_book.py
    │   log.log
```