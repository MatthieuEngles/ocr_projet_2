import argparse
import logging
from pydoc import doc
import logging_loki
import requests
import pandas as pd
from bs4 import BeautifulSoup
from lxml import html
import regex
import os


#region definition de constante
APP_NAME = 'OpenClassRoom projet_2' #Nom de l'application pour les logs
DEFAULT_URL = 'http://books.toscrape.com/' #url par défaut sinon précisé par l'utilisateur
DICT_STARS = {
                'One':1,
                'Two':2,
                'Three':3,
                'Four':4,
                'Five':5,
            }
#endregion

#region initialisation du logger
logging_loki.emitter.LokiEmitter.level_tag = "level"
handler = logging_loki.LokiHandler(
    url="http://20.0.0.200:3100/loki/api/v1/push",
    tags={"application": APP_NAME},
    version="1",
)

logger = logging.getLogger("my-logger")
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)
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
                    help="Choisissez en repertoire de sortie (par default : \"data\")",
                    default="data")

parser.add_argument("-c", "--category",
                    metavar='\b', 
                    help="Choisissez la catégorie de livre à scrapper (par default : Toutes (\"None\"))",
                    default=None)

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
    try:
        currency_unit = regex.findall(r'\p{Sc}', price)[0]
        return float(price.replace(currency_unit,''))
    except Exception as e:
        logger.error("Erreur de fonction", extra={"tags": {"function":'convert_price', "Paramètre":price}})
        return None
    
def get_number_in_string(s):
    """Renvoie le premier entier isolé trouvé dans une chaine de caractères,l'entier peut être précédé de "(" sans espace, toutes les parenthèse ouvrante sont ignorées

    Args:
        s (string): chaine de caractère contenant au moins un entier

    Returns:
        int: le premier entier de la chaine d'entrée
    """
    try:
        value = [int(s) for s in s.replace('(','').split() if s.isdigit()][0]
    except Exception as e:
        logger.error("Erreur de fonction", extra={"tags": {"function":'get_number_in_string',"Paramètre":s}})
        raise Exception
    

def find_specific_td_in_table(table,text_search,delta=1):
    """Renvoie la valeur de la cellule d'un tableau sur la meme ligne : 
        si le texte recherché est un td : avec une décalage de colonne de "delta"
        si le texte recherché est un th : on renvoie le premier td de la ligne

    Args:
        table (string): tableau dans lequel rechercher sous forme de soup de tr / td 
        text_search (string): texte titre du champs rechercher
        delta (int, optional): décalage de colonne. Defaults to 1.

    Returns:
        string: valeur du champ rechercher si aucun champ trouver renvoi None
    """
    for tr in table.findAll('tr'):
        if tr.find('th'):
            if tr.find('th').text == text_search:
                return  tr.find('td').text.strip()
        else:
            i=0
            for td in tr.findAll('td'):
                if td.text == text_search:
                    return  tr.findAll('td')[i+delta].text.strip()
                i+=1
    
    return None

def get_stars_rating(soup):
    """Renvoi le nombre d'étoile d'un livre

    Args:
        soup (bs4.class.array): Liste des classes de la soupe d'entrée sous forme de tuple(array)

    Returns:
        int: nombre d'étoile
    """
    return DICT_STARS[soup[0][1]]
#endregion

class Book():
    def __init__(self,product_page_url,universal_product_code,title,price_including_tax,price_excluding_tax,number_available,product_description,category,review_rating,image_url):
        self.product_page_url=product_page_url,
        self.universal_product_code=universal_product_code,
        self.title=title,
        self.price_including_tax=price_including_tax,
        self.price_excluding_tax=price_excluding_tax,
        self.number_available=number_available,
        self.product_description=product_description,
        self.category=category,
        self.review_rating=review_rating,
        self.image_url=image_url
        #ensuite on nettoie les valeurs
        self.transform_clean_book()
        
    def transform_clean_book(self):
        self.price_including_tax=convert_price(self.price_including_tax),
        self.price_excluding_tax=convert_price(self.price_excluding_tax),
        self.number_available=get_number_in_string(self.number_available),
        self.product_description=self.product_description.strip(),
        self.review_rating=get_stars_rating(self.review_rating),
        
    def to_dict(self):  
        return{
            "product_page_url":self.product_page_url,
            "universal_product_code":self.universal_product_code,
            "title":self.title,
            "price_including_tax":self.price_including_tax,
            "price_excluding_tax":self.price_excluding_tax,
            "number_available":self.number_available,
            "product_description":self.product_description,
            "category":self.category,
            "review_rating":self.review_rating,
            "image_url":self.image_url,
        }

    def to_pandas(self):
        return pd.DataFrame({
            "product_page_url":[self.product_page_url],
            "universal_product_code":[self.universal_product_code],
            "title":[self.title],
            "price_including_tax":[self.price_including_tax],
            "price_excluding_tax":[self.price_excluding_tax],
            "number_available":[self.number_available],
            "product_description":[self.product_description],
            "category":[self.category],
            "review_rating":[self.review_rating],
            "image_url":[self.image_url],
                })


def get_category(url,category):
    """Renvoie l'url de la catégorie fournie en entrée

    Args:
        url (string): url du site
        category (string): catégorie recherchée

    Returns:
        string: url de la catégoerie
    """
    reponse = requests.get(url)
    soup = BeautifulSoup(reponse.text,features="lxml")
    soup = soup.find('div',{'class':'side_categories'})
    for li in soup.find_all('a'):
        if li.text.strip()==category:
            return url+li['href']
    return None


#region extract et classeter spécifiques au projet
def get_url_page(num_page):
    return f'http://books.toscrape.com/catalogue/page-{num_page}.html'

def get_url_category_page(url_base,num_page):
    return url.replace('index.html',f'page-{num_page}.html')

def get_book_from_url(url):
    reponse = requests.get(url)
    soup = BeautifulSoup(reponse.text,features="lxml")
    table = soup.find('table',{'class':'table table-striped'})

    product_page_url = url
    universal_product_code = find_specific_td_in_table(table,'UPC')
    title = soup.find('div',{'class':'product_main'}).find('h1').text.strip()
    price_including_tax = find_specific_td_in_table(table,'Price (incl. tax)')
    price_excluding_tax = find_specific_td_in_table(table,'Price (excl. tax)')
    number_available = find_specific_td_in_table(table,'Availability')
    product_description = soup.find('article',{'class':'product_page'}).text.strip()
    category = find_specific_td_in_table(table,'UPC')
    review_rating = soup.find('p',{'class':'star-rating'})['class']
    image_url = soup.find('div',{'class':'carousel-inner'}).find('img')['src'] 
    return Book(product_page_url,universal_product_code,title,price_including_tax,price_excluding_tax,number_available,product_description,category,review_rating,image_url)

def get_list_books_url(url_base):
    reponse = requests.get(url_base)
    soup = BeautifulSoup(reponse.text,features="lxml")
    list_url_soup = soup.find('ol',{'class':'row'}).findAll('a')
    list_url = []
    for l in list_url_soup:
        list_url.append(l['href'])
    
    list_url_final = []
    for url in list_url:
        url_modif = url
        url_base_modif = url_base
        while url_modif[:3]=='../':
            url_modif = url_modif[3:]
            url_base_modif = '/'.join(url_base_modif.split('/')[:-1])
        list_url_final.append(url_base_modif+'/'+url_modif)
    
    return list_url_final
#endregion


#region load
def creation_repertoire_sortie(rep):
    try:
        os.mkdir(rep)
    except Exception as e:
        logger.error("Erreur de fonction", extra={"tags": {"function":'creation_repartoire_sortie', "Paramètre":rep, "Erreur":e}})       


def save_list_book(list_book,rep):
    try:
        books = pd.concat([b.to_pandas() for b in list_book])
        books.reset_index(drop=Tue,inplace=True)
        books.to_csv(rep+'/books.csv')
        logger.info(f"Liste de livre enregistrer") 
    except Exception as e:
        logger.error("Erreur de fonction", extra={"tags": {"function":'save_list_book', "Paramètre":rep, "Erreur":e}})     
#endregion






#region point d'entrée
if __name__ == "__main__":
    logger.info("Démarrage de l'application")


    url_to_scrap = args.src
    category = args.category
    output_dir = args.outputdir
    logger.info(f"Lecteur parametre url : {url_to_scrap}")       
    logger.info(f"Lecteur parametre category : {category}")  
    logger.info(f"Lecteur parametre output : {output_dir}") 
    
    
    #test si la catégorie fait plus d'une page
    url = get_category(url_to_scrap,category)
    if category:
        url = get_category(url_to_scrap,category)
        reponse = requests.get(get_url_category_page(url,1))
        if reponse.status_code==200:
            None
         
    
    
    #lecture des livres
    page_to_scrap = 1
    reponse = requests.get(get_url_category(url,page_to_scrap))
    # while reponse.status_code == 200:
        


    
    
    # creation_repartoire_sortie(output_dir)
    # absolute_path = os.path.dirname(__file__)


    # book = get_book_from_url('http://books.toscrape.com/catalogue/scott-pilgrims-precious-little-life-scott-pilgrim-1_987/index.html')
    # print(book.to_dict())
    print(get_category(url_to_scrap,'Christian'))
    
    liste = get_list_books_url(get_category(url_to_scrap,'Christian'))
    for l in liste:
        print(l)
#endregion
