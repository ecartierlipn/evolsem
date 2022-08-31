# inspiré de https://github.com/ian-nai/PyGallica/blob/master/python3/search_api.py
import os,sys,pickle
import glob
import re
import json
import shutil
import xmltodict
from bs4 import BeautifulSoup
from xml.etree import ElementTree as ET
import pandas as pd
from ast import literal_eval
import traceback
import logging
import logging.config
from datetime import datetime

# mysql
import mysql.connector
from mysql.connector import Error
import traceback

# mysql connection parameters
host = 'localhost'
user = 'root'
password = 'neoveille'
db = 'evolsem'

# utility function to retry requests if failed (frequent with gallica)
import requests
from requests.adapters import HTTPAdapter
#from requests.packages.urllib3.util.retry import Retry
from urllib3.util.retry import Retry



def select_words_from_mysql(table="lexies", fields=['word_lemma','part_of_speech'], debug=False):
    '''
        Connect to MySQL database and select fields from table
        Parameters
        ----------
        table : TYPE str
        the table name
        fields : TYPE array of strings
        the fields to retrieve
        Returns
        -------
        the result as a dict (word => pos)
    '''
    print("selecting fields into database/table : " + db + '.' + table + " . Fields : " + str(len(fields)))
    try:
        conn = mysql.connector.connect(host=host,
                                       database=db,
                                       user=user,
                                       password=password,
                                       autocommit=True)
        if conn.is_connected():
            cursor = conn.cursor()
            res = {}
            q = "select " + ",".join(fields) + ' from ' + table
            #print(q)
            cursor.execute(q)
            for row in cursor:
                #print(row)
                res[row[0]] = row[1]
            return True, res
        else:
            return False, "connection error"
    except Exception as e:
        var = traceback.format_exc()
        print("Error in : select_words_from_mysql. Error : \n" + var)                            
        if debug == True:
            exit()
        else:
            return False, var

def requests_retry_session(retries=5,backoff_factor=0.3,status_forcelist=(500, 502, 503, 504),session=None):
    try:
        session = session or requests.Session()
        retry = Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session
    except Exception as e:
        log.error("Problem with this request. Reason :" + str(e))
        return False

# Word synthesis through the whole corpus : generate a <word>.synthesis.json file in outputdir

def search_synthesis(word,outputdir):
    query = 'gallica all "' + word + '"'
    url = 'https://gallica.bnf.fr/services/Categories?SRU='
    try:
        s = requests_retry_session().get(url+query, stream=True)
        s.raise_for_status()
    except requests.exceptions.HTTPError as err:
        raise SystemExit(err)

    #log.info(s.content)
    with open(outputdir + word + ".synthesis.json", "w") as write_file:
        json.dump(s.json(), write_file, indent=4)

# Word occurrences (without contexts) : generate a <word>.json file in outputdir (Search.search2)
# inspiré de https://github.com/ian-nai/PyGallica/blob/master/python3/search_api.py

# Full documentation for this API can be found on Gallica's site: http://api.bnf.fr/api-gallica-de-recherche
# see also : http://catalogue.bnf.fr/api/test.do

class Search(object):
    
    @staticmethod
    def search(*args, savetofile=True, outputfile="gallica.xml"):    
        RECHERCHE_BASEURL = 'https://gallica.bnf.fr/SRU?operation=searchRetrieve&version=1.2&query=(gallica all '
        START_REC = ')&startRecord=1'
    
        for arg in args:
            search_string = (', '.join('"' + item + '"' for item in args))
      
        url = "".join([RECHERCHE_BASEURL, search_string, START_REC])
        log.info(url)

        s = requests_retry_session().get(url, stream=True)
        soup = BeautifulSoup(s.content,"lxml-xml")
        #log.info(soup)
        if savetofile:
            with open(outputfile, 'wb') as f:
                f.write(soup.prettify().encode('UTF-8'))
                f.close()
            with open(outputfile) as xml:
                doc = xmltodict.parse(xml.read())
                return doc
        else:
            doc = xmltodict.parse(soup.prettify().encode('UTF-8'))
            return doc

    # new method
    @staticmethod
    def search2(query='', *otherargs,  savetofile=True, outputfile="gallica.xml"):
        if savetofile==True and os.path.isfile(outputfile):
            try:
                with open(outputfile) as fd:
                    doc = xmltodict.parse(fd.read())
                    return doc
            except Exception as e:
                os.remove(outputfile)
                Search.search2(query,otherargs,savetofile,outputfile)
            
        RECHERCHE_BASEURL = 'https://gallica.bnf.fr/SRU?operation=searchRetrieve&version=1.2'
        QUERY = '&query=(' + query + ')'
        START_REC = ')&startRecord=1'
        OTHER_ARGS=''
        for arg in otherargs:
            OTHER_ARGS = OTHER_ARGS + '&' + arg
      
        url = "".join([RECHERCHE_BASEURL, QUERY, OTHER_ARGS])
        log.info(url)
        
        try:
            s = requests_retry_session().get(url, stream=True)
            s.raise_for_status()
        except requests.exceptions.HTTPError as err:
            log.error("HTTPError : " + str(err))
            return False
            #raise SystemExit(err)
        
        soup = BeautifulSoup(s.content,"lxml-xml")
        #log.info(soup)
        if savetofile:
            with open(outputfile, 'wb') as f:
                f.write(soup.prettify().encode('UTF-8'))
                f.close()
            with open(outputfile) as xml:
                doc = xmltodict.parse(xml.read())
                return doc
        else:
            doc = xmltodict.parse(soup.prettify().encode('UTF-8'))
            return doc

# Document search (for contexts) Full documentation for this API can be found on Gallica's site: http://api.bnf.fr/api-document-de-gallica

class Document(object):

    @staticmethod
    def issues(id):
    
        ISSUES_BASEURL = 'https://gallica.bnf.fr/services/Issues?ark=ark:/'
    
        url = "".join([ISSUES_BASEURL, id, '/date'])
        log.info(url)
    
        s = requests_retry_session().get(url, stream=True)
        soup = BeautifulSoup(s.content,"lxml-xml")
        log.info(soup)
        file = open('issues.xml', 'w')
        file.write(soup.prettify().encode('UTF-8'))
        file.close()
        with open('issues.xml') as xml:
            doc = xmltodict.parse(xml.read())
            return doc
            
    @staticmethod
    def issues_date(id, date):
    
        ISSUESDATE_BASEURL = 'https://gallica.bnf.fr/services/Issues?ark=ark:/'
      
        url = "".join([ISSUESDATE_BASEURL, id, '/date', '&date=', date])
        log.info(url)
    
        s = requests_retry_session().get(url, stream=True)
        soup = BeautifulSoup(s.content,"lxml-xml")
        #log.info(soup)
        file = open('issues_date.xml', 'w')
        file.write(soup.prettify().encode('UTF-8'))
        file.close()
        with open('issues_date.xml') as xml:
            doc = xmltodict.parse(xml.read())
            return doc
    @staticmethod
    def metadata_date(id, tmpdir='./tmp/'):
    
        tmpfile = tmpdir + '.' + id + '.xml'
        # get url only if xml file does not already exist
        if os.path.isfile(tmpfile) is False:
            OAI_BASEURL = 'https://gallica.bnf.fr/services/OAIRecord?ark='
            url = "".join([OAI_BASEURL, id])
            log.info(url)
            try:
                s = requests_retry_session().get(url, stream=True)
                soup = BeautifulSoup(s.content,"lxml-xml")
                file = open(tmpfile, 'wb')
                file.write(soup.prettify().encode('UTF-8'))
                file.close()
            except Exception as e:
                log.error("Error with this file : " + tmpfile + ". Error : " + str(e))
                os.remove(tmpfile)
                return ['', '']

        with open(tmpfile) as xml:
            doc = xmltodict.parse(xml.read())
            #log.info(doc)
            #return doc
            try:
                res = doc['results']['notice']['record']['metadata']['oai_dc:dc']
                if 'dc:identifier' in res:
                    id = res['dc:identifier']
                else :
                    id= ''
                if 'dc:date' in res:
                    date = res['dc:date']
                else :
                    date= ''
                os.remove(tmpfile)
                return [id, date]
            except Exception as e:
                log.error("Error with this file : " + tmpfile + ". Error : " + str(e))
                os.remove(tmpfile)
                return ['', '']
        
    @staticmethod
    def OAI(id):
    
        OAI_BASEURL = 'https://gallica.bnf.fr/services/OAIRecord?ark=ark:/'
    
        url = "".join([OAI_BASEURL, id])
        log.info(url)
    
        s = requests_retry_session().get(url, stream=True)
        soup = BeautifulSoup(s.content,"lxml-xml")
        file = open('oai.xml', 'w')
        file.write(soup.prettify().encode('UTF-8'))
        file.close()
        with open('oai.xml') as xml:
            doc = xmltodict.parse(xml.read())
            return doc
            
    @staticmethod
    def pagination(id):
    
        PAGINATION_BASEURL = 'https://gallica.bnf.fr/services/Pagination?ark=ark:/'
    
        url = "".join([PAGINATION_BASEURL, id])
        log.info(url)
    
        s = requests_retry_session().get(url, stream=True)
        soup = BeautifulSoup(s.content,"lxml-xml")
        file = open('pagination.xml', 'w')
        file.write(soup.prettify().encode('UTF-8'))
        file.close()
        with open('pagination.xml') as xml:
            doc = xmltodict.parse(xml.read())
            return doc
            
    @staticmethod
    def simple_images(id, res):
    
        IMAGES_BASEURL = 'https://gallica.bnf.fr/ark:/'
    
        url = "".join([IMAGES_BASEURL, id, '/', res])
        log.info(url)
    
        response = requests_retry_session().get(url, stream=True)
        with open('simple_image.jpg', 'wb') as out_file:
            shutil.copyfileobj(response.raw, out_file)
            del response
    
    @staticmethod
    def content(id, query):
    
        CONTENT_BASEURL = 'https://gallica.bnf.fr/services/ContentSearch?ark='
    
        url = "".join([CONTENT_BASEURL, id, '&query=', query])
        log.info(url)
    
        s = requests_retry_session().get(url, stream=True)
        soup = BeautifulSoup(s.content,"lxml-xml")
        file = open('content.xml', 'w')
        file.write(soup.prettify().encode('UTF-8'))
        file.close()
        with open('content.xml') as xml:
            doc = xmltodict.parse(xml.read())
            return doc
    
    @staticmethod
    def content_page(id, query, page):
    
        CONTENTPAGE_BASEURL = 'https://gallica.bnf.fr/services/ContentSearch?ark='
    
        url = "".join([CONTENTPAGE_BASEURL, id, '&query=', query, '&page=', page])
        log.info(url)
    
        s = requests_retry_session().get(url, stream=True)
        soup = BeautifulSoup(s.content,"lxml-xml")
        file = open('content_page.xml', 'w')
        file.write(soup.prettify().encode('UTF-8'))
        file.close()
        with open('content_page.xml') as xml:
            doc = xmltodict.parse(xml.read())
            return doc

    # new function
    @staticmethod
    def content_search(id, query, tmpdir='./tmp/'):
    
        tmpfile = tmpdir + query + '.'+id + '.xml'
        # get url only if xml file does not already exist
        if os.path.isfile(tmpfile) is False:
            CONTENTPAGE_BASEURL = 'https://gallica.bnf.fr/services/ContentSearch?ark='
            url = "".join([CONTENTPAGE_BASEURL, id, '&query=', query])
            log.info(url)
            try:
                s = requests.get(url)
                #s = requests_retry_session().get(url, stream=True)
                soup = BeautifulSoup(s.content,"lxml-xml")
                file = open(tmpfile, 'wb')
                file.write(soup.prettify().encode('UTF-8'))
                file.close()
            except Exception as e:
                log.error("Impossible to get url :" + url)
                return [0,[]]
        with open(tmpfile) as xml:
            try:
                doc = xmltodict.parse(xml.read())
            except Exception as e:
                log.error('Error with doc = xmltodict.parse(xml.read())' + str(e))
                return [0,[]]
            #log.info(doc)
            #return doc
            res = doc['results']['items']
            log.info(str(doc['results']['@countResults']) + ' result(s)')
            nbres = doc['results']['@countResults']
            #log.info(nbres)
            if nbres=='0':
                #return [nbres,[res['item']['p_id'],res['item']['content']]]
                return [nbres,[]]
            elif nbres=='1':
                #return [nbres,[res['item']['p_id'],res['item']['content']]]
                return [nbres,[res['item']['content']]]
            else:
                #log.info(res)
                resitems=[]
                try:
                    resitems = [elt['content'] for elt in res['item']]
                    #log.info(len(resitems))
                    #if len(resitems)==0:
                    #    log.info(res)
                    return [nbres, resitems]
                except Exception as e:
                    log.error("Error with :\n" + str(res) + "\nError : " + str(e))
                    return [nbres, resitems]
        
    @staticmethod
    def toc(id):
    
        TOC_BASEURL = 'https://gallica.bnf.fr/services/Toc?ark='
    
        url = "".join([TOC_BASEURL, id])
        log.info(url)
    
        s = requests_retry_session().get(url, stream=True)
        soup = BeautifulSoup(s.content,"lxml-xml")
        file = open('toc.xml', 'w')
        file.write(soup.prettify().encode('UTF-8'))
        file.close()
        with open('toc.xml') as xml:
            doc = xmltodict.parse(xml.read())
            return doc
            
    @staticmethod
    def texte_brut(id):
        TEXTEBRUT_BASEURL = 'https://gallica.bnf.fr/ark:/'
    
        url = "".join([TEXTEBRUT_BASEURL, id, '.texteBrut'])
        log.info(url)
    
        s = requests_retry_session().get(url, stream=True)
        soup = BeautifulSoup(s.content,"lxml-xml")
        file = open('textebrut.xml', 'wb')
        file.write(soup.prettify().encode('UTF-8'))
        file.close()
        return soup
        #with open('textebrut.xml') as xml:
        #    doc = xmltodict.parse(xml.read())
        #    return doc
            
    @staticmethod
    def ocr(id, page):
        OCR_BASEURL = 'https://gallica.bnf.fr/RequestDigitalElement?O='
    
        url = "".join([OCR_BASEURL, id, '&E=ALTO&Deb=', page])
        log.info(url)
    
        s = requests_retry_session().get(url, stream=True)
        soup = BeautifulSoup(s.content,"lxml-xml")
        #log.info(soup)
        file = open('ocr.xml', 'w')
        file.write(soup.prettify().encode('UTF-8'))
        file.close()
        with open('ocr.xml') as xml:
            doc = xmltodict.parse(xml.read())
            return doc


####################################################################  MYSQL Save functions
  
def save_lexies_to_mysql(table, data, ignore=True):
    '''
        Connect to MySQL database and insert data into table
        Parameters
        ----------
        db : TYPE str 
        the database name
        table : TYPE str
        the table name
        data : TYPE array of dict
        The data to insert as an array of dict with required information
        Returns
        -------
        True|False : TYPE boolean
        the fate of the query
    '''
    print("Inserting data into database/table : " + db + '.' + table + " . Data entries : " + str(len(data)))
    try:
        conn = mysql.connector.connect(host=host,
                                       database=db,
                                       user=user,
                                       password=password,
                                       autocommit=True)
        if conn.is_connected():
            conn.get_warnings = True
            #print('Connected to Mysql database' + "\n")
            cursor = conn.cursor()
            if ignore :
                mysql_cmd = "INSERT IGNORE INTO "
            else:
                mysql_cmd = "INSERT INTO "
            warnings = []
            for row in data:
                #print(row)
                cursor.execute(mysql_cmd + table + """ (word_lemma,language,main_morph,freq_c1,freq_c2,part_of_speech)
                    VALUES (%(word_lemma)s,%(language)s,%(word_lemma)s,%(freq_c1)s,%(freq_c2)s,%(part_of_speech)s) ON DUPLICATE KEY UPDATE
                     freq_c1="%(freq_c1)s", freq_c2="%(freq_c2)s" """, row)
                conn.commit()
                warning = cursor.fetchwarnings()
                if warning:
                    warnings.append({str(warning) : row})
            return True, warnings
        else:
            return False, "Connection to the server error"
    except Exception as e:
        var = traceback.format_exc()
        print("Error in : def save_lexies_to_mysql(table, data):. Error : \n" + var)                            
        return False, var

def update_lexies_def_to_mysql(table, data, debug=False):
    '''
        Connect to MySQL database and update definitions from wikt data into table
        Parameters
        ----------
        db : TYPE str 
        the database name
        table : TYPE str
        the table name
        data : TYPE array of dict
        The data to insert as an array of dict with required information
        Returns
        -------
        True|False : TYPE boolean
        the fate of the query
    '''
    print("Updating data into database/table : " + db + '.' + table + " . Data entries : " + str(len(data)))
    try:
        conn = mysql.connector.connect(host=host,
                                       database=db,
                                       user=user,
                                       password=password,
                                       autocommit=True)
        if conn.is_connected():
            #print('Connected to Mysql database' + "\n")
            cursor = conn.cursor()
            for elt in data:
                definition =  re.sub(r"\[\]", "", data[elt]) + "<a href='https://fr.wiktionary.org/wiki/" + re.sub(" ","_",elt) + "' target='new'><i class='fa fa-external-link' style='color:blue;'></i></a>"
                if debug:
                    print(elt)
                q = "UPDATE " + table + ' SET definition="' + definition + '" where word_lemma="' + elt + '";'
                if debug:
                    print(q)
                try:
                    cursor.execute(q)
                    conn.commit()
                except mysql.connector.Error as err:
                    print("Mysql Error : {}".format(err))
                    print("Query :" , q)
                    exit()

            return True, True
        else:
            return False, "Connection to the server error"
    except Exception as e:
        var = traceback.format_exc()
        print("Error in : def update_lexies_def_to_mysql:. Error : \n" + var)                            
        return False, var

def update_lexies_freq_to_mysql(table, data):
    '''
        Connect to MySQL database and update frequency from wikt data into table
        Parameters
        ----------
        db : TYPE str 
        the database name
        table : TYPE str
        the table name
        data : TYPE array of dict
        The data to insert as an array of dict with required information
        Returns
        -------
        True|False : TYPE boolean
        the fate of the query
    '''
    print("Updating data into database/table : " + db + '.' + table + " . Data entries : " + str(len(data)))
    try:
        conn = mysql.connector.connect(host=host,
                                       database=db,
                                       user=user,
                                       password=password,
                                       autocommit=True)
        if conn.is_connected():
            #print('Connected to Mysql database' + "\n")
            cursor = conn.cursor()
            for elt in data:
                #print(row)
                cursor.execute("UPDATE " + table + ' SET freq_c1="' + data[elt][0] + '", freq_c2="'+ data[elt][1] + '" where word_lemma="' + elt + '";')
                conn.commit() 
            return True, True
        else:
            return False, "Connection to the server error"
    except Exception as e:
        var = traceback.format_exc()
        print("Error in : def update_lexies_freq_to_mysql:. Error : \n" + var)                            
        return False, var

def update_lexies_corpus_freq_to_mysql(table, word, freq, corpus):
    '''
        Connect to MySQL database and update frequency from wikt data into table
        Parameters
        ----------
        db : TYPE str 
        the database name
        table : TYPE str
        the table name
        data : TYPE array of dict
        The data to insert as an array of dict with required information
        Returns
        -------
        True|False : TYPE boolean
        the fate of the query
    '''
    print("Updating data into database.table : " + db + '.' + table + " . Word  : " + word + ", corpus : " + corpus + ", frequency : " + freq)
    try:
        conn = mysql.connector.connect(host=host,
                                       database=db,
                                       user=user,
                                       password=password,
                                       autocommit=True)
        if conn.is_connected():
            #print('Connected to Mysql database' + "\n")
            cursor = conn.cursor()
            if corpus == 'jsi':
                cursor.execute("UPDATE " + table + ' SET freq_c2="' + freq + '" where word_lemma="' + word + '";')
                conn.commit() 
                return True, True
            elif corpus=="eur":
                cursor.execute("UPDATE " + table + ' SET freq_c1="' + freq + '" where word_lemma="' + word + '";')
                conn.commit() 
                return True, True
            else:
                return False, "Bad corpus name : " + corpus

            
        else:
            return False, "Connection to the server error"
    except Exception as e:
        var = traceback.format_exc()
        print("Error in : def update_lexies_freq_to_mysql:. Error : \n" + var)                            
        return False, var


def save_sentences_to_mysql(table, data, debug=False):
    '''
        Connect to MySQL database and insert data into table
        Parameters
        ----------
        db : TYPE str 
        the database name
        table : TYPE str
        the table name
        data : TYPE array of dict
        The data to insert as an array of dict with required information
        Returns
        -------
        True|False : TYPE boolean
        the fate of the query
    '''
    print("Inserting data into database/table : " + db + '.' + table + " . Data entries : " + str(len(data)))
    try:
        conn = mysql.connector.connect(host=host,
                                       database=db,
                                       user=user,
                                       password=password,
                                       autocommit=True)
        if conn.is_connected():
            #print('Connected to Mysql database' + "\n")
            cursor = conn.cursor()
            for row in data:
                #print(row)
                #exit()
                try:
                    cursor.execute("INSERT IGNORE INTO " + table + """ (word,pos,key_word,corpus,journal,url,date,sentence) # IGNORE
                        VALUES (%(word)s,%(pos)s,%(key_word)s,%(corpus)s,%(journal)s,%(url)s,%(date)s,%(sentence)s)""", row)
                    conn.commit() 
                except Exception as e:
                    var = traceback.format_exc()
                    print("Error in : save_sentences_to_mysql. Error : \n" + var) 
                    if debug == True:
                        print(row)
                        print("Error in : save_sentences_to_mysql ", var)
                        exit()
                    else:
                        print("Error in : save_sentences_to_mysql ", var)
                        return False, var
            return True, True
        else:
            return False, "connection error"
    except Exception as e:
        var = traceback.format_exc()
        print("Error in : save_sentences_to_mysql. Error : \n" + var)                            
        if debug == True:
            exit()
        else:
            return False, var

############################ main - test
#tmpdir='./tmp/'
#snippets = Document.content_search('bpt6k9683436d', 'taxer',tmpdir)
#log.info(snippets)
#metadata = Document.metadata_date('bpt6k9683436d')
#log.info(metadata)
#exit()
#text = Document.texte_brut('ark:/12148/cb32747166k')
#log.info(str(text))

############################ main ############################################
##############################################################################
def main():
    # define task(s) and words
    tasks = ['word_sythesis','corpus_synthesis','word_documents','word_contexts','clean_word_contexts','contexts_embeddings','word_contexts_mysql','all']
    task = ['all']
    from_wordlist = 'word' # 'file', 'pickle','word'
    word_filter = [15] # ie noun, 15 for verb
    #word_pos = {'verre':'15', 'rose', 'vestiaire', 'volupté', 'voile', 'voyou', 'volant', 'zeste', 'rouge', 'volume', 'vitrifier', 'blanc', 'volée', 'veste', 'verge', 'vilain', 'jaune', 'brun', 'vulgate', 'zélote', 'zinc', 'vert', 'violet', 'visite', 'vignette', 'vortex', 'volubilité', 'vestige', 'visa', 'vilaine', 'virement', 'orange', 'zéphyr', 'vedette', 'œillet', 'bleu', 'vogue', 'noir', 'gris'}

    ############### retrieve wordlists
    # read candidat lists for verbs and nouns
    if from_wordlist =='word':
        vlist = ['téléphone']
    elif from_wordlist =='pickle':
        data = pickle.load(open("../contextual_embeddings/FrenchSemEval-1.1-191210/FSE-1.1.data.xmlverbs_sentence_nb.pkl", mode="rb"))
        #print(data)
        vlist = list(data.keys())
    elif from_wordlist=='file':
        log.info("retrieving word list")
        verbes = {}
        with open('liste_candidats_verbes_vieilli.txt') as fin:
            for line in fin:
                a =  re.search(r"^([^_]+)_[0-9]", line)
                if a:
                    verbes[re.sub(r"\s*\*",'',a.group(1).strip())]="V"
                    #log.info(a.group(1))
        vlist = sorted(verbes, reverse=True)
        #log.info(vlist)
        noms = {}
        with open('liste_candidats_noms_vieilli.txt') as fin:
            for line in fin:
                a =  re.search(r"^([^_]+)_[0-9]", line)
                if a:
                    noms[re.sub(r"\s*\*",'',a.group(1).strip())]="N"
        nlist = sorted(noms, reverse=True)
        nlist.extend(vlist)
        log.info(str(nlist) +  str(len(nlist)) + "elements")
    elif from_wordlist=='file_csv':
        log.info("retrieving word list from simple csv file")
        verbes={}
        with open('liste-mots.csv') as fin:
            for line in fin:
                a =  re.search(r"^\w+(-\w+)?$", line.strip())
                if a:
                    verbes[line.strip()]="X"
                    #log.info(a.group(1))
        vlist = sorted(verbes, reverse=True)
        log.info(str(vlist) +  str(len(vlist)) + "elements")
    elif from_wordlist=='mysql':
        log.info("retrieving word list from mysql")
        truefalse, verbes = select_words_from_mysql()
        if word_filter and truefalse:
            vlist = {k:v for k,v in verbes.items() if v in word_filter } # and re.match("[f-z]",k)
            vlist = list(vlist.keys())
        elif truefalse:
            vlist = verbes
        else:
            log.error("No words retrieved. Check mysql query")
            print("No words retrieved. Check mysql query")
            exit()


    log.info("*"*20 + "\nLauching processs with following paramaters\nTasks : " + str(tasks) + "\nWordlist : " +  str(vlist) +  "\n" + "*"*20)
    print("*"*20 + "\nLauching processs with following paramaters\nTasks : " + str(tasks) + "\nWordlist : " +  str(vlist) +  "\n" + "*"*20)
    #exit()
    #################### launch process 0 . From words retrieve occurrences synthesis (API recherche GALLICA : Categories)
    # => <word>.synthesis.json in output dir

    if 'word_sythesis' in task or 'all' in task:
        log.info("*"*10 + "Task : word_sythesis")
        outputdir = './gallica_output/synthesis/'
        print("*"*10 + "Task : word_sythesis", ", check outputdir : " + outputdir)
        os.makedirs(outputdir, exist_ok=True)
        #nlist=['taxer']
        for word in vlist:
            word=word.strip()
            if os.path.isfile(outputdir + word + '.synthesis.json'):
                log.info("Already done for " + word + " in file : " + outputdir + word + '.synthesis.json')
                continue
            log.info("Generating synthesis for " + word + " in file : " + outputdir + word + '.synthesis.json')
            search_synthesis(word,outputdir)

    #################### launch process 1. From words retrieve all occurrences (without contexts) (API recherche GALLICA : searchRetrieve)
    # # => <word>.json in output dir

    # 1.a. retrieve corpus synthesis (monographies et fascicules ie périodiques)
    # pour les différents types de corpus (1700-1950)
    corplist = ['monographie','fascicule']

    if 'corpus_synthesis' in task or 'all' in task:
        log.info("*"*10 +  " Task : corpus_synthesis")
        outputdir = './gallica_output/'
        print("*"*10 + "Task : corpus_synthesis", ", check outputdir : " + outputdir)

        os.makedirs(outputdir, exist_ok=True)

        for corp in corplist:
            log.info("Searching : " + corp)
            if os.path.isfile(outputdir + corp + ".json"):
                log.info("already analyzed corpus : " + corp + ' in ' + outputdir + corp + ".json")
                continue
            data=[]
            for year in range(1700,1950):
                query = '(dc.language all "fre") and (dc.type all "' + corp + '") and (access all "fayes") and (ocr.quality all "Texte disponible") and (gallicapublication_date>="' + str(year) + '/01/01" and gallicapublication_date<="' + str(year) + '/12/31")'
                res = Search.search2(query,
                            'startRecord=1','maximumRecords=2', 'collapsing=false',
                            savetofile=False)
                nbres = int(res['srw:searchRetrieveResponse']['srw:numberOfRecords'])
                log.info(str(nbres) + " occurences")
                data.append({'year': year, 'total':nbres})

            with open(outputdir + corp + ".json", "w") as write_file:
                json.dump(data, write_file, indent=4)
            log.info("results for : " + corp + ' in ' + outputdir + corp + ".json")


    # 1.b. retrieve word occurrences (attention ici on se limite aux fascicules)


    if 'word_documents' in task or 'all' in task:
        log.info("*"*10 + " Task : word_documents")
        outputdir = './gallica_output/'
        print("*"*10 + "Task : word_documents", ", check outputdir : " + outputdir)
        os.makedirs(outputdir, exist_ok=True)
        missing={}
        for word in vlist:
            word = word.strip()
            log.info("Searching : " + word)
            if os.path.isfile(outputdir + word + ".json"):
                log.info("already analyzed word : " + word + ' in file ' + outputdir + word + ".json" )
                continue
            query = 'gallica all "'+ word + '"' +  ' and dc.language all "fre" and dc.type all "fascicule" and access all "fayes" and ocr.quality all "Texte disponible"'
            data = []    
            res = Search.search2(query,
                            'startRecord=1','maximumRecords=50', 
                            savetofile=True, outputfile=outputdir + word + ".1.xml" )

            nbres = int(res['srw:searchRetrieveResponse']['srw:numberOfRecords'])
            log.info(str(nbres) + " to parse")
            if nbres > 0:
                for elt in res['srw:searchRetrieveResponse']['srw:records']['srw:record']:
                    eltdata = elt['srw:recordData']['oai_dc:dc']
                    #log.info(eltdata)
                    eltdata2 = elt['srw:extraRecordData']
                    for d in eltdata2:
                        eltdata[d]= eltdata2[d]
                    #eltdata2 = elt['srw:recordData']['oai_dc:dc']
                    #for d in eltdata2:
                    #    eltdata[d]= eltdata2[d]
                    data.append(eltdata)
            else:
                log.info("No result for this word : " + word)
                missing[word] = "No result"
                continue
            pos = 51
            while pos < nbres:
                log.info("StartRecord Position to parse : " + str(pos))
                #time.sleep(3)
                try:
                    res = Search.search2(query,
                                'startRecord='+str(pos),'maximumRecords=50', 
                                savetofile=True, outputfile=outputdir + word +  "." + str(pos) + ".xml" )
                except Exception as e:
                    log.error("Error : " + str(e) + ". Skipping this entry.")
                    missing[word] = str(e)
                    continue
                if res and res['srw:searchRetrieveResponse']['srw:records'] is not None:
                    for elt in res['srw:searchRetrieveResponse']['srw:records']['srw:record']:
                        try:
                            eltdata = elt['srw:recordData']['oai_dc:dc']
                            #log.info(eltdata)
                            eltdata2 = elt['srw:extraRecordData']
                            for d in eltdata2:
                                eltdata[d]= eltdata2[d]
                            data.append(eltdata)
                        except Exception as e:
                            log.error("Error : " + str(e) + ". Skipping this entry.")
                            missing[word] = str(e)
                            continue
                pos = pos + 50
            
            with open(outputdir + word + ".json", "w") as write_file:
                json.dump(data, write_file, indent=4)
            log.info("Analyzed word : " + word + ' in file ' + outputdir + word + ".json" )
            # delete xml file for the word (all is saved in json file)
            files = glob.glob(outputdir + word + "*.xml")
            for file in files:
                os.remove(file)
        if len(missing)> 0:
            log.info('All is done except for specific words. Please check : ' + os.path.basename(__file__) + '.word_documents.errors.json')
            json.dump(missing, open('./log/' + os.path.basename(__file__) + '.word_documents.errors.json', mode='w'), indent=4)
        else:
            log.info("All is done")




    #################### launch process 2 . From previous json file retrieve contexts (API Gallica Document)
    #  and save all information in one xlsx file : <word>.xlsx


    if 'word_contexts' in task or 'all' in task:
        log.info("*"*10 + " Task : word_contexts")
        outputdir = './gallica_output/'
        print("*"*10 + "Task : word_contexts", ", check outputdir : " + outputdir)
        os.makedirs(outputdir, exist_ok=True)
        tmpdir='./tmp/'
        os.makedirs(tmpdir, exist_ok=True)
        century = '' #ie 19 or 20
        word_errors={}

        for word in vlist:
            word=word.strip()
            if os.path.isfile(outputdir + word + '.xlsx'):
                log.info("Already parsed : " + word + ' in ' + outputdir + word + '.xlsx')
                continue
            if os.path.isfile(outputdir + word + '.json') is False:
                log.info("No json input file : " + word + '(' + outputdir + word + '.json)')
                word_errors[word]= "No json input file : " + outputdir + word + '.json'
                continue
            try:
                log.info("Parsing : " + word)
                df = pd.read_json(outputdir + word + '.json')
                # drop rows where uri is none
                #log.info(df.info())
                df.dropna(subset=['uri'], inplace=True)
                #log.info(df.info())
                # get contexts
                df[['nbresults','contexts']] = df.apply(lambda x : Document.content_search(str(x['uri']), word,tmpdir), axis = 1, result_type ='expand')
                df[['dc:identifier','datetime']] = df.apply(lambda x : Document.metadata_date(str(x['uri'])), axis = 1, result_type ='expand')

            # save dataframe to excel
                df = df.explode('contexts')
                df.to_excel(outputdir+word+'.xlsx',index=False)
                log.info("Done for word " + word +  " in file " + outputdir+word+'.xlsx')
                # delete xml file for the word (all is saved in json file)
                files = glob.glob(tmpdir + word + "*.xml")
                for file in files:
                    os.remove(file)
            except Exception as e:
                log.error("Error while parsing " + word + '. Error : ' + str(e))
                word_errors[word]= "Error while parsing. Error : " + str(e)
                continue

        if len(word_errors)> 0:
            log.info('All is done except for specific words. Please check : ' + os.path.basename(__file__) + '.word_contexts.errors.json')
            json.dump(word_errors, open('./log/' + os.path.basename(__file__) + '.word_contexts.errors.json', mode='w'), indent=4)
        else:
            log.info("All is done")
            #except Exception as e:
            #    log.info("Error with " + w + ', error : ' + str(e))

    # obsolete : now we directly store into mysql
    if 'word_contexts_neoveille' in tasks:
        outputdir = './gallica_output/'
        os.makedirs(outputdir, exist_ok=True)

        for word in vlist:
            word=word.strip()
            if os.path.isfile(outputdir + word + '.neoveille.csv'):
                log.info("Already generated for " + word + ' (' + outputdir + word + '.neoveille.csv)')
                continue
            if os.path.isfile(outputdir + word + '.xlsx') is False:
                log.info("You first need to generate the XLSX file from previous step (word_contexts task) : " + word)
                continue
            try:
                log.info("Parsing : " + word)
                df = pd.read_excel(outputdir + word + '.xlsx')
                df[['dc:identifier', 'dc:publisher', 'dc:title',
                    'dc:type', 'dc:creator', 
                    'link', 'typedoc', 'dc:subject',
                    'datetime', 'contexts']].to_csv(outputdir + word + '.neoveille.csv', index=False)
            except Exception as e:
                log.error("Error" + str(e))

    # for saving into mysql
    if 'all' in task or 'clean_word_contexts' in task:
        log.info("*"*10 + " Task : clean_word_contexts")
        word_errors={}
        input_dir ='./gallica_output/'
        output_dir = './gallica_output/'
        print("*"*10 + "Task : clean_word_contexts", ", check outputdir : " + outputdir)
        corpus= 'gallica'
        lang= 'fra'
        for w in vlist:
            w=w.strip()
            try:
                if os.path.exists(input_dir + w + '.xlsx') is False:
                    log.info("No input file for for : " + w + '(' + input_dir + w + '.xlsx)')
                    word_errors[w] = "Path does not exist / skipping : " + input_dir + w + '.xlsx)'
                    continue
                if os.path.exists(output_dir+ corpus + '.'+ w + '.clean.xlsx'):
                    log.info("Already generated file for " + w + ' (' + output_dir+ corpus + '.'+ w + '.clean.xlsx)' )
                    continue
                #log.info("persing " + w)
                df = pd.read_excel(input_dir + w + '.xlsx')
                #log.info(df.info())
                df.dropna(subset=['datetime','contexts','dc:identifier','dc:source'],inplace=True)
                #log.info(df.info())
                #log.info("parsing : " + w, df.shape[0], ' initial entries')
                # delete nqamoyen < 0.80
                df = df[df.nqamoyen > 80]
                #log.info("after nqamoyen > 80 : " + w, df.shape[0], ' entries')
                df.rename(columns={'dc:identifier':'url','contexts':'sentence','dc:title':'journal','datetime':'date2','nqamoyen':'ocr_quality'}, inplace=True)
                df['corpus']='gallica'
                df['word']=w
                df['key_word'] = df['sentence'].str.extract(r"<span class=\'highlight\'>(.+?)<\/span>",expand=True)
                df['key_word'] = df['key_word'].str.lower()
                #log.info(df.key_word.value_counts())
                df.dropna(subset=['key_word'],inplace=True)
                df['sentence'].replace(to_replace="<span class='highlight'>", value="<mark>", regex=True, inplace=True)  
                df['sentence'].replace(to_replace="<\/span>", value="</mark>", regex=True, inplace=True)  
                #log.info(df['date2'].unique())
                df['date']= pd.to_datetime(df['date2'], errors='coerce', infer_datetime_format=True)
                errors = df.loc[df['date'].isnull()]['date2'].unique().tolist()
                df = df[~df.date.isin(errors)].copy()
                df = df[df.date.dt.year > 1799]
                df['year'] = df.date.dt.year
                # source
                def parse_journal(x):
                    #print(x)
                    if re.match(r"\[[\'\"]",x):
                        try:
                            #res = literal_eval(x)
                            res = eval(x)
                            return res[0]
                        except:
                            var = traceback.format_exc()
                            log.error('Error with ' + w + ". Error : \n" + var)                            
                            return x
                    elif re.match(r"\[",x):
                        res = re.sub(r"[\[\]]",'',x)
                        return res
                    else:
                        return x
                df['journal'] = df['journal'].apply(parse_journal)
                df[['year','url', 'journal','sentence','word','key_word','ocr_quality']].to_excel(output_dir+ corpus + '.'+ w + '.clean.xlsx', index=False)
                log.info("File saved for word " + w + '('+output_dir+ corpus + '.'+ w + '.clean.xlsx)')
            except Exception as e:
                var = traceback.format_exc()
                log.error('Error with ' + w + ". Error : \n" + var)
                #log.error("Error with " + w + ', error : ' + str(e))
                word_errors[w] = str(e)
        if len(word_errors)> 0:
            log.info('All is done except for specific words. Please check : ' + os.path.basename(__file__) + '.clean_word_contexts.errors.json')
            json.dump(word_errors, open('./log/' + os.path.basename(__file__) + '.clean_word_contexts.errors.json', mode='w'), indent=4)
        else:
            log.info("All is done")

    # save to mysql (contexts and lexies)
    if 'word_contexts_mysql' in task:
        log.info("*"*10 + " Task : word_contexts_mysql")
        word_errors={}
        input_dir ='./gallica_output/'
        output_dir = './gallica_output/'
        print("*"*10 + "Task : word_contexts_mysql", ", check outputdir : " + output_dir)
        corpus= 'gallica'
        lang= 'fra'
        files = glob.glob(input_dir+"*.clean.xlsx")
        files = [f for f in files if  datetime.utcfromtimestamp(os.path.getctime(f)).date() > datetime.strptime('2022-02-02', '%Y-%m-%d').date() ]
        #for f in files:
        #    print(f, datetime.utcfromtimestamp(os.path.getctime(f)).date())
        #print(files)
        #exit()
        words = [f.split('/')[-1].split('.')[1] for f in files]
        print(words, len(words))
        #exit()
        for f in files:
            w = f.split('/')[-1].split('.')[1]
            print("Parsing : ", w)
            w=w.strip()
            try:
                df = pd.read_excel(f)#input_dir + corpus + '.' + w + '.clean.xlsx'
                df.drop_duplicates(inplace=True)
                print("Initial shape : ", df.shape)
                df = df[df.key_word.str.contains(r"^"+w+r".?$", regex=True)]
                print("Shape after filtering word form : ", df.shape)
                freq1 = df.shape[0]
                #print(df.info(verbose=True))
                #exit()
                print("word forms : ", df.key_word.value_counts())
                #print(df['sentence'].head())
                #exit()
                update_lexies_corpus_freq_to_mysql("wiktionary_lexicon", w, str(freq1), "gallica")
                print("storing contexts in db")
                df['pos']=''
                df['corpus']='gallica'
                df['journal']= df['journal'].str.slice(0,250)
                df['datetime'] = pd.to_datetime(df['year'], format='%Y') # , ignore_errors=True, errors='raise'
                df['date'] = df['datetime'].dt.strftime('%Y-%m-%d').astype(str)
                #df['year']= str(df['year'])+'-01-01'
                #df.rename(columns = {'year':'date'}, inplace=True)
                if df.shape[0]>10000:
                    df = df.sample(n=10000, random_state=5)
                res, detail = save_sentences_to_mysql('sentences2', df[['word','pos','key_word','corpus','journal','url','date','sentence']].to_dict(orient='records'), debug=True)
            except Exception as e:
                var = traceback.format_exc()
                log.error('Error with ' + w + ". Error : \n" + var)
                #log.error("Error with " + w + ', error : ' + str(e))
                word_errors[w] = str(e)
        if len(word_errors)> 0:
            log.info('All is done except for specific words. Please check : ' + os.path.basename(__file__) + '.clean_word_contexts.errors.json')
            json.dump(word_errors, open('./log/' + os.path.basename(__file__) + '.clean_word_contexts.errors.json', mode='w'), indent=4)
        else:
            log.info("All is done")
        
    # for parsing with word/token embeddings
    if 'all' in task or 'contexts_embeddings' in task:
        log.info("*"*10 + " Task : contexts_embeddings")
        word_errors={}
        input_dir ='./gallica_output/'
        output_dir = '../visualization/input_files/'
        print("*"*10 + "Task : contexts_embeddings", ", check outputdir : " + outputdir)
        corpus= 'gallica'
        lang= 'fra'
        for w in vlist:
            w=w.strip()
            try:
                if os.path.exists(input_dir + w + '.xlsx') is False:
                    log.info("No input file for for : " + w + '(' + input_dir + w + '.xlsx)')
                    word_errors[w] = "Path does not exist / skipping : " + input_dir + w + '.xlsx)'
                    continue
                if os.path.exists(output_dir+ corpus + '.'+ w + '.csv'):
                    log.info("Already generated file for " + w + ' (' + output_dir+ corpus + '.'+ w + '.csv)' )
                    continue
                #log.info("persing " + w)
                df = pd.read_excel(input_dir + w + '.xlsx')
                #log.info(df.info())
                df.dropna(subset=['datetime','contexts','dc:identifier','dc:source'],inplace=True)
                #log.info(df.info())
                #log.info("parsing : " + w, df.shape[0], ' initial entries')
                # delete nqamoyen < 0.80
                df = df[df.nqamoyen > 95]
                #log.info("after nqamoyen > 80 : " + w, df.shape[0], ' entries')
                df.rename(columns={'dc:identifier':'url','contexts':'sentence','dc:title':'journal','datetime':'date2'}, inplace=True)
                df['corpus']='gallica'
                df['word']=w
                df['key_word'] = df['sentence'].str.extract(r"<span class=\'highlight\'>(.+?)<\/span>",expand=True)
                df['key_word'] = df['key_word'].str.lower()
                #log.info(df.key_word.value_counts())
                df.dropna(subset=['key_word'],inplace=True)
                df['sentence'].replace(to_replace="<span class='highlight'>", value="", regex=True, inplace=True)  
                df['sentence'].replace(to_replace="<\/span>", value="", regex=True, inplace=True)  
                #df["sentence"].replace(to_replace=r"^(.{40,}?)\(\.\.\.\)", value=r'\1', regex=True,inplace=True)
                #log.info(df['date2'].unique())
                df['date']= pd.to_datetime(df['date2'], errors='coerce', infer_datetime_format=True)
                errors = df.loc[df['date'].isnull()]['date2'].unique().tolist()
                df = df[~df.date.isin(errors)].copy()
                df = df[df.date.dt.year > 1799]
                df['year'] = df.date.dt.year
                df[['year','sentence','key_word']].to_csv(output_dir+ corpus + '.'+ w + '.csv', index=False)
                log.info("File saved for word " + w + '('+output_dir+ corpus + '.'+ w + '.csv)')
            except Exception as e:
                log.error("Error with " + w + ', error : ' + str(e))
                word_errors[w] = str(e)
        if len(word_errors)> 0:
            log.info('All is done except for specific words. Please check : ' + os.path.basename(__file__) + '.contexts_embeddings.errors.json')
            json.dump(word_errors, open('./log/' + os.path.basename(__file__) + '.contexts_embeddings.errors.json', mode='w'), indent=4)
        else:
            log.info("All is done")


######### main
if __name__ == '__main__':
    log_dir = './log'
    os.makedirs('./log', exist_ok=True) 
    logstream = 'file'
    if logstream == 'file':
        print("messages sent to log file : " + log_dir + '/' + os.path.basename(__file__) + ".log")
        FORMAT = "%(levelname)s:%(asctime)s:%(message)s[%(filename)s:%(lineno)s - %(funcName)s()]"
        logging.basicConfig(format=FORMAT, datefmt='%m/%d/%Y %I:%M:%S %p', filename=log_dir + '/' + os.path.basename(__file__) + ".log",filemode="w", level=logging.INFO)    
        log = logging.getLogger(__name__)
        #logger = logging.getLogger()
        #log.info("redirecting 
        # print statements to log file : " + log_dir + '/' + os.path.basename(__file__) + ".log")
        #sys.stderr.write = log.error
        #sys.stdout.write = log.info
    else:
        FORMAT = "%(levelname)s:%(asctime)s:%(message)s[%(filename)s:%(lineno)s - %(funcName)s()]"
        logging.basicConfig(format=FORMAT, datefmt='%m/%d/%Y %I:%M:%S %p',stream=sys.stdout, level=logging.INFO)
        log = logging.getLogger(__name__)
    main()
