import argparse
import logging
from pydoc import doc
import logging_loki
import requests
import pandas
from bs4 import BeautifulSoup
from lxml import html
import regex
import os

#region definition de constante
APP_NAME = 'OpenClassRoom projet_2' #Nom de l'application pour les logs
DEFAULT_URL = 'http://books.toscrape.com/' #url par défaut sinon précisé par l'utilisateur
#endregion

#region initialisation du logger
logging_loki.emitter.LokiEmitter.level_tag = "level"
handler = logging_loki.LokiHandler(
    url="http://molp.fr:3100/loki/api/v1/push", 
    version="1",
)

logger = logging.getLogger("my-logger")
logger.addHandler(handler)

logger.info(
    "Démarrage de l'application", 
    extra={"tags": {"app": APP_NAME}},
)

#endregion


# logging.debug('This message should go to the log file')
# logging.info('So should this')
# logging.warning('And this, too')
# logging.error('And non-ASCII stuff, too, like Øresund and Malmö')

#region initialisation du parseur d'argument
parser = argparse.ArgumentParser(usage='use "%(prog)s --help" for more information',
                                 description='Ce programme va extraire les informations des livres du catalogue d\'un site internet. \n'+
                                             'Par défaut un dossier "data" sera créé pour sauvegarder les données extraites.',
                                 allow_abbrev=True,
                                )

parser.add_argument("-s", "--src",
                    metavar='\b', 
                    help=f"Choisissez le site à scrapper (par defaut : {DEFAULT_URL} ", 
                    default=DEFAULT_URL)

parser.add_argument("-o", "--outputdir",
                    metavar='\b', 
                    help="Choisissez en repertoire de sortie (par default : \"/data\")", 
                    default="/data")

parser.add_argument("-c", "--category",
                    metavar='\b', 
                    help="Choisissez en repertoire de sortie (par default : \"/data\")", 
                    default="/data")

args = parser.parse_args()
#endregion

#region fonction genérales
def convert_price(price):
    """Renvoie la valeur numérique d'une chaine de caractère indicant l'unité de monnaie
    Args:
        price (string): montant financier au format string avec la monnaie indiquée type: €, £ ou EUR, USD

    Returns:
        float: valeur en numérique (float) de la valeur d'entrée
    """
    
    currency_unit = regex.findall(r'\p{Sc}', price)[0]
    return float(price.replace(currency_unit,''))

def get_number_in_string(s):
    """Renvoie le premier entier isolé trouvé dans une chaine de caractères,l'entier peut être précédé de "(" sans espace, toutes les parenthèse ouvrante sont ignorées

    Args:
        s (string): chaine de caractère contenant au moins un entier

    Returns:
        int: le premier entier de la chaine d'entrée
    """
    return [int(s) for s in s.replace('(','').split() if s.isdigit()][0]
#endregion

class Book():
    def __init__(self,product_page_url,universal_product_code,title,price_including_tax,price_excluding_tax,number_available,product_description,category,review_rating,image_url):
        self.item={
            "product_page_url":product_page_url,
            "universal_product_code":universal_product_code,
            "title":title,
            "price_including_tax":price_including_tax,
            "price_excluding_tax":price_excluding_tax,
            "number_available":number_available,
            "product_description":product_description,
            "category":category,
            "review_rating":review_rating,
            "image_url":image_url,
        }


#region fonctions et classeter spécifiques au projet
def get_url_page(num_page):
    return f'http://books.toscrape.com/catalogue/page-{num_page}.html'



def get_book_from_url(url):
    reponse = requests.get(url)
    # soup = BeautifulSoup(reponse.text)
    tree = html.fromstring(reponse.content)    
    product_page_url = url
    universal_product_code = tree.xpath('/html/body/div[1]/div/div[2]/div[2]/article/table/tr[1]')[0].text_content().strip()
    title = tree.xpath('/html/body/div[1]/div/div[2]/div[2]/article/div[1]/div[2]/h1')[0].text_content()
    price_including_tax = convert_price(tree.xpath('/html/body/div[1]/div/div[2]/div[2]/article/table/tr[4]/td')[0].text_content())
    price_excluding_tax = convert_price(tree.xpath('/html/body/div[1]/div/div[2]/div[2]/article/table/tr[3]/td')[0].text_content())
    number_available = get_number_in_string(tree.xpath('/html/body/div[1]/div/div[2]/div[2]/article/table/tr[6]/td')[0].text_content())
    product_description = tree.xpath('/html/body/div[1]/div/div[2]/div[2]/article/p')[0].text_content()
    category = tree.xpath('/html/body/div[1]/div/ul/li[3]/a')[0].text_content()
    review_rating = tree.xpath('/html/body/div[1]/div/div[2]/div[2]/article/div[1]/div[2]/p[3]')[0].text_content()
    image_url = tree.xpath('/html/body/div[1]/div/div[2]/div[2]/article/div[1]/div[1]/div/div/div/div/img/@src')[0]
    return Book(product_page_url,universal_product_code,title,price_including_tax,price_excluding_tax,number_available,product_description,category,review_rating,image_url)



#region point d'entrée
if __name__ == "__main__":
    print(args.verbose)
    absolute_path = os.path.dirname(__file__)
    print(absolute_path)
#endregion
