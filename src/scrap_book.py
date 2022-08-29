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
from datetime import datetime
import inspect
import sys
from urllib.parse import urljoin
from tqdm import tqdm

#region definition de constante
APP_NAME = 'OpenClassRoom projet_2 Test' #Nom de l'application pour les logs
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
    url="http://molp.fr:3100/loki/api/v1/push",
    tags={"application": APP_NAME},
    version="1",
)

logger = logging.getLogger(APP_NAME)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)
is_log_to_file = True
log_file = 'log.log'
is_log_to_var = True
log_var = []
is_verbose=False

def log_to_file(time, statuts,message, func_name, data_in, exception, log_file_to = log_file):
    """Enregistre les logs un fichier

    Args:
        time (str): heure
        statuts (str): status du log
        message (str): message du log
        func_name (str): fonction qui log
        data_in (str): données d'entrée
        exception (str): message de l'exception
        log_file (str): fichier du log 
    """
    with open(log_file_to,'a', encoding = 'utf-8') as f:
        f.write(time.ljust(30)+
                statuts.ljust(10)+
                message.ljust(30)+
                func_name.ljust(30)+
                data_in.ljust(30)+
                exception.ljust(30)+
                '\n')

def log_to_var(time, statuts,message, func_name, data_in, exception):
    """Enregistre les logs dans une variable

    Args:
        time (_type_): heure
        statuts (_type_): status du log
        message (_type_): message du log
        func_name (_type_): fonction qui log
        data_in (_type_): données d'entrée
        exception (_type_): message de l'exception
    """
    log_var.append({'time':time,
            'status': statuts,
            'message':message,
            'fonction':func_name,
            'data_in':data_in,
            'exception':exception
            })

def log_to_console(time, statuts='',message='', func_name='', data_in='', exception=''):
    """ Affiche les logs dans la console

    Args:
        time (str): heure
        statuts (str, optional): status du log. Defaults to ''.
        message (str, optional):  message du log. Defaults to ''.
        func_name (str, optional):  fonction qui log. Defaults to ''.
        data_in (str, optional): données d'entrée. Defaults to ''.
        exception (str, optional):  message de l'exception. Defaults to ''.
    """
    print(time, statuts,message,func_name,data_in,exception)
    
def log_error(message,data_in,exception):
    """fonction qui permet de logger une erreur

    Args:
        message (str): status du log
        data_in (Object): données d'entrée
        exception (Exception): exception
    """
    time = datetime.now().isoformat(timespec='seconds', sep=' ')
    try:
        func_name = sys._getframe(1).f_code.co_name
    except Exception as _e:
        func_name = 'main'
    try:
        logger.error('error',extra={"tags": {"message": message, 
                                             "function":func_name, 
                                             "input":str(data_in), 
                                             "exception":str(exception), 
                                             'date-time': time}})
    except Exception as _e:
        logger.error('error',extra={"tags": {"message": message, 
                                             "function":func_name, 
                                             "input":'', 
                                             "exception":str(exception), 
                                             'date-time': time}})
    if is_log_to_file:
        log_to_file(time, 'ERROR', '',func_name,str(data_in),str(exception) )
    if is_log_to_var:
        log_to_var(time, 'ERROR', '',func_name,str(data_in),str(exception) )
    if is_verbose:
        log_to_console(time, 'ERROR', '',func_name,str(data_in),str(exception) )

def log_info(message):
    """Fonction qui permet de logger une info

    Args:
        message (str): message
    """
    time = datetime.now().isoformat(timespec='seconds', sep=' ')
    try:
        func_name = sys._getframe(1).f_code.co_name
    except Exception as _e:
        func_name = 'main'
    logger.info('info',extra={"tags": {"message": message, 
                                       "function":func_name, 
                                       "input":"", 
                                       "exception":"", 
                                       'date-time':time}})
    if is_verbose:
        log_to_console(time, message)
#endregion


# logging.debug('This message should go to the log file')
# logging.info('So should this')
# logging.warning('And this, too')
# logging.error('And non-ASCII stuff, too, like Øresund and Malmö')

#region initialisation du parseur d'argument
parser = argparse.ArgumentParser(usage='use "%(prog)s --help" for more information',
                                 description='Ce programme va extraire les informations \
                                              des livres du catalogue d\'un site internet. \n'+
                                             'Par défaut un dossier "data" sera créé pour \
                                            sauvegarder les données extraites.',
                                 allow_abbrev=True,
                                )

parser.add_argument("-s", "--src",
                    metavar='\b', 
                    help=f"Choisissez le site à scrapper (par defaut : {DEFAULT_URL})",
                    default=DEFAULT_URL)

parser.add_argument("-o", "--outputdir",
                    metavar='\b', 
                    help="Choisissez en repertoire de sortie (par default : \"data\")",
                    default="data")

parser.add_argument("-c", "--category",
                    metavar='\b', 
                    help="Choisissez la catégorie de livre à scrapper \
                         (par default : Toutes (\"None\"))",
                    default=None)

parser.add_argument("-v", "--verbose",
                    help="Affiche les logs dans la console",
                    action='store_true',
                    )

args = parser.parse_args()
#endregion

#region fonction genérales
def convert_price(price):
    """Renvoie la valeur numérique d'une chaine de caractère indicant l'unité de monnaie
    
    Args:
        price (string): montant financier au format string 
                        avec la monnaie indiquée type: €, £ ou EUR, USD

    Returns:
        float: valeur en numérique (float) de la valeur d'entrée
    """
    try:
        currency_unit = regex.findall(r'\p{Sc}', price)[0]
        return float(price.replace(currency_unit,''))
    except Exception as _e:
        log_error('',price,_e)
        return None

def get_number_in_string(s):
    """Renvoie le premier entier isolé trouvé dans une chaine de caractères,
    l'entier peut être précédé de "(" sans espace, toutes les parenthèse ouvrante sont ignorées

    Args:
        s (string): chaine de caractère contenant au moins un entier

    Returns:
        int: le premier entier de la chaine d'entrée
    """
    try:
        value = [int(s) for s in s.replace('(','').split() if s.isdigit()][0]
        return value
    except Exception as _e:
        log_error('',s,_e)        
        return None


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
                    return  tr.findAll('td')[i+delta].text
                i+=1

    return None

def get_stars_rating(soup):
    """Renvoi le nombre d'étoile d'un livre

    Args:
        soup (bs4.class.array): Liste des classes de la soupe d'entrée sous forme de tuple(array)

    Returns:
        int: nombre d'étoile
    """
    return DICT_STARS[soup[1]]
#endregion

class Book():
    def __init__(self,product_page_url,universal_product_code,title,price_including_tax,
                 price_excluding_tax,number_available,product_description,
                 category,review_rating,image_url):
        self.product_page_url=product_page_url
        self.universal_product_code=universal_product_code
        self.title=title
        self.price_including_tax=price_including_tax
        self.price_excluding_tax=price_excluding_tax
        self.number_available=number_available
        self.product_description=product_description
        self.category=category
        self.review_rating=review_rating
        self.image_url=image_url
        #ensuite on nettoie les valeurs
        self.transform_clean_book()

    def transform_clean_book(self):
        """Traite et transforme les information du livre
        """
        self.price_including_tax=convert_price(self.price_including_tax)
        self.price_excluding_tax=convert_price(self.price_excluding_tax)
        self.number_available=get_number_in_string(self.number_available)
        self.product_description=self.product_description
        self.review_rating=get_stars_rating(self.review_rating)
        self.image_url = urljoin(self.product_page_url,self.image_url)
        self.category=self.category.strip().lower().replace(' ','-')
        self.product_description=self.product_description.strip().replace(';',',')
    def to_dict(self):
        """ renvoi le livre sous forme de dictionnaire

        Returns:
            dict: livre sous forme de dictionnaire
        """
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
        """ renvoi le livre sous forme de dataframe

        Returns:
            Pandas Dataframe: livre sous forme de dataframe
        """
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
    try:
        _reponse = requests.get(url)
        soup = BeautifulSoup(_reponse.text,features="lxml")
        soup = soup.find('div',{'class':'side_categories'})
        for li in soup.find_all('a'):
            if li.text.strip().lower().replace(' ','-')==category:
                return urljoin(url,li['href'])
        return None
    except Exception as _e:
        log_error('', [url,category],_e)
        return None

#region extract et classeter spécifiques au projet
def get_url_page(url_base, num_page):
    """Genere l'url de la page num_page
       Attention, uniquement valide pour la page de test

    Args:
        url_base (str): url_de base
        num_page (int): numéro de la page recherchée

    Returns:
        str: url de sortie
    """
    return f'{url_base}/catalogue/page-{num_page}.html'

def get_url_category_page(url_base,num_page):
    """Renvoie l'url paginée on essaie de remplacer "index.html" par "page-{num_page}.html"

    Args:
        url_base (str): url de base 
        num_page (int): numéro de pages

    Returns:
        str: url de sortie
    """
    try:
        return url_base.replace('index.html',f'page-{num_page}.html')
    except Exception as _e:
        log_error('', [url_base,num_page],_e)
        return None

def get_book_from_url(url):
    """Renvoi un object livre à partir d'un url

    Args:
        url (str): url du livre

    Returns:
        Book: le livre
    """
    try:
        _reponse = requests.get(url)
        soup = BeautifulSoup(_reponse.text,features="lxml")
        table = soup.find('table',{'class':'table table-striped'})

        product_page_url = url
        universal_product_code = find_specific_td_in_table(table,'UPC')
        title = soup.find('div',{'class':'product_main'}).find('h1').text.strip()
        price_including_tax = find_specific_td_in_table(table,'Price (incl. tax)')[1:]
        price_excluding_tax = find_specific_td_in_table(table,'Price (excl. tax)')[1:]
        number_available = find_specific_td_in_table(table,'Availability')
        product_description = soup.find('article',{'class':'product_page'})\
                              .findAll('p')[3].text
        category = soup.find('ul',{'class':'breadcrumb'}).findAll('li')[-2].text
        review_rating = soup.find('p',{'class':'star-rating'})['class']
        image_url = soup.find('div',{'class':'carousel-inner'}).find('img')['src']
        return Book(product_page_url,
                    universal_product_code,
                    title,
                    price_including_tax,
                    price_excluding_tax,
                    number_available,
                    product_description,
                    category,
                    review_rating,
                    image_url)

    except Exception as _e:
        log_error('',url,_e)
        return None

def get_list_books_url(url_base):
    """Renvoie la liste des url de tous les livres présent sur la page

    Args:
        url_base (str): url a scrapper

    Returns:
        list: liste d'url pour tous les livres de la page
    """
    _reponse = requests.get(url_base)
    soup = BeautifulSoup(_reponse.text,features="lxml")
    list_url_soup = soup.find('ol',{'class':'row'}).findAll('a')
    list_url = []
    for l in list_url_soup:
        list_url.append(urljoin(url_base, l['href']))

    return list_url
#endregion


#region load
def creation_repertoire_sortie(rep):
    """Créer les répertoire de sortie {rep}, {rep}/data et {rep}/images 

    Args:
        rep (str): répertoire à créer
    """
    try:
        os.mkdir(rep)
        os.mkdir(rep+'/books')
        os.mkdir(rep+'/images')
    except Exception as _e:
        log_error('',rep,_e)
        return None

def save_list_book(list_book,output_dir):
    """Enregistre la liste des livres en csv dans le répertoire spécifié

    Args:
        list_book (list[Book]): la liste de livres à enregistrer
        output_dir (str): le répertoire de sortie

    """
    try:
        books = pd.concat([b.to_pandas()for b in list_book])
        books.reset_index(drop=True,inplace=True)
        list_category = books.category.unique()
        for cat in list_category:
            books[books.category==cat].to_csv(f'{output_dir}/books/{cat}.csv',sep=';',index=False)
        log_info(f"Liste de livre enregistré")
    except Exception as _e:
        log_error('',output_dir,_e)
        return None

def get_image_from_book(book,output_dir):
    """Télécharge et enregistre l'image du livre

    Args:
        book (Book): le livre dont il faut télécharger et enregistrer l'image
        output_dir (str): le repertoire parent de destination

    """
    try:
        url = book.image_url
        image_name = url.split('/')[-1]
    except Exception as _e:
        log_error('',book,_e)
        return None 

    try:
        _response = requests.get(url)
        if _response.status_code == 200:
            with open(f"{output_dir}/images/{image_name}", 'wb') as f:
                f.write(_response.content)
    except Exception as _e:
        log_error('',[url,image_name],_e)
        return None

#endregion

#region point d'entrée
if __name__ == "__main__":
    log_info(f"App Start")       

    url_to_scrap = args.src
    category = args.category
    output_dir = args.outputdir

    if category is not None:
        category = category.lower()

    if args.verbose:
        is_verbose=True
        print("########## VERBOSE ############")

    log_info(f"Lecteur parametre url : {url_to_scrap}")       
    log_info(f"Lecteur parametre category : {category}")  
    log_info(f"Lecteur parametre output : {output_dir}")

    #on créer les répertoire de sortie
    creation_repertoire_sortie(output_dir)

    liste_url_book=[] #variable contentant toutes les url des livres à scraper
    liste_book=[] #variable contentant toutes livres (class Book)
    url = get_category(url_to_scrap,category)
    try:
        if category is not None:
            log_info(f"Catégorie: {category} - Scrapping des url de chaque livre")

            url_cat = get_category(url_to_scrap,category) #on récupère l'url de la catégorie
            #on essaie de lire la page 1 pour voir si c'est multipage
            reponse = requests.get(get_url_category_page(url_cat,1)) 
            if reponse.status_code==200: #si la réponse est ok c'est qu'il s'agit d'un multipage
                page_to_scrap = 1 #on crée un compteur sur la page 1
                while reponse.status_code == 200:  #tant que la réponse est Ok on continue
                    try:
                        # on scrape la page page_to_scrap
                        url = get_url_category_page(url_cat,page_to_scrap) 
                        print(url,page_to_scrap )
                        reponse = requests.get(url)
                        if reponse.status_code == 200:
                            #on stocke tous les url des livres dans une listes 
                            liste_url_book = liste_url_book+get_list_books_url(url) 
                            page_to_scrap += 1 # on passe à la page suivante
                    except Exception as _e:
                        log_error('',url,_e)

            else: #si la réponse est Non ok c'est qu'il s'agit d'une page seule
                #on stocke tous les url des livres dans une listes
                liste_url_book = liste_url_book+get_list_books_url(url) 
        else: #si aucune des catégorie n'est précisé
            page_to_scrap = 1 #on crée un compteur sur la page 1
            url = get_url_page(url_to_scrap,page_to_scrap)
            log_info(f"Aucune catégorie - Scrapping des url de chaque livre")

            reponse = requests.get(url)
            #tant que la réponse est Ok on continue
            while reponse.status_code == 200:
                try : 
                    url = get_url_page(url_to_scrap,page_to_scrap)
                    log_info(f"Scrap en cours URL : {url}")
                    try:
                        reponse = requests.get(url)
                    except Exception as e:
                        log_error('',url,e)

                    if reponse.status_code == 200:
                        #on stocke tous les url des livres dans une listes 
                        liste_url_book = liste_url_book+get_list_books_url(url)
                        page_to_scrap += 1 # on passe à la page suivante
                except Exception as _e:
                    log_error('',url,_e)

    except Exception as _e:
        log_error('',url,_e)
        
    liste_url_book = list(set(liste_url_book))
    log_info(f"{len(liste_url_book)} livres trouvés")
    log_info(f"Scrapping des informations des livres en cours")

    #on scrappe tous les url des livres:
    liste_book = []
    for url in tqdm(liste_url_book):
        liste_book.append(get_book_from_url(url))

    #on enregistre la liste des livres:
    save_list_book(liste_book,output_dir)

    #on télécharge toutes les images:
    for b in tqdm(liste_book):
        get_image_from_book(b,output_dir)

    nb_error = len(log_var)
    if nb_error!=0:
        print('###########')
        print(f'Le programme à recontré {nb_error} erreur(s), consultez les logs')
    else:
        print('Tout c\'est bien déroulé, le programme n\'a pas rencontré d\'erreur')
    print('###########')
    print('Fin du programme')
    print('###########')

#endregion
