# ocr_projet_2

## Description
Le programme permet d'extraire les informations concernant les livres d'un site de vente en ligne.

## Installation
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
3. Lancez le programme
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