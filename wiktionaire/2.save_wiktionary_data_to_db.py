from numpy.core.numeric import False_
import numpy as np
import pandas as pd
import os, re,json
# see https://dev.mysql.com/doc/connector-python/en/  
import mysql.connector
from mysql.connector import Error
import traceback
 # solr functions
import pysolr, json, requests
import os,re
import glob
import pandas as pd
import time


# mysql connection parameters
host = 'localhost'
user = 'root'
password = 'neoveille'
db = 'evolsem'


######################################################################### SketchEngine API

USERNAME = 'ecartierdijon21000'
API_KEY = '8627c3386edb448383fb30d5999d3334'
#USERNAME = 'ecartierlipn'
#API_KEY = 'baba4579828d497fb3bd64613a8db4fe'
base_url = 'https://api.sketchengine.eu/bonito/run.cgi'


corpus = 'preloaded/fra_jsi_newsfeed_virt'
################################################# sketchengine query parameters
# ## generic paramteters for sketchengine API query
params = {
 'format': 'json', # format de la réponse (attention au 30/03/2020 : métainformations disponibles seulement avec json!)
 'async':0, # mode de réponse (ici on récupère toute la réponse, c'est plus long mais plus facile à gérer)
 #'corpname': 'preloaded/frantext_trends',
 'attrs': 'word,lemma,tag', # informations pour le mot clé
 'ctxattrs': 'word,lemma,tag', # idem pour les mots du contexte
 #'q':'q[word="afro.+"]', # query
 'viewmode':'sen', # on récupère le mode sentence (phrase vs kwic)
 'pagesize':1, # nbre de résultats maximum
}
cmd = 'view' # concordance search
params['corpname']= corpus
corp_fn = params['corpname'].split('/')

#################################################################### SketchEngine API (JSI corpus freq)

# retrieve corpus info from sketchengine
def corpus_info(corpus):
	''' get corpus info'''
	params = {'gramrels':1, 'registry':1, 'struct_attr_stats':1,'subcorpora':1}
	params['corpname']=corpus
	res =  requests.get(base_url + '/corp_info', params=params, auth=(USERNAME, API_KEY)).json()
	if 'error' in res.keys():
		print("Error in result for query : [" + base_url + '/corp_info?], params : ' + str(params) + ', error : '+ res['error'])
		return False
	else :
		#print(res)
		return res

# generic sketchengine search (depends on params, see below for wordlist and view queries) 
def query_sketchengine(params, cmd):
  '''Cette fonction envoie une requête à sketchengine et retourne la réponse
  voir https://www.sketchengine.eu/documentation/methods-documentation/ pour tous les paramètres'''
  try:
    if params['format']=='json':
      res = requests.get(base_url + '/' + cmd, params=params, auth=(USERNAME, API_KEY), timeout=120).json()
    else:
      res = requests.get(base_url + '/' + cmd, params=params, auth=(USERNAME, API_KEY), timeout=120)
    return res, True
  except Exception as e:
    var = traceback.format_exc()
    print("Error in : def 'query_sketchengine'. Error : \n" + var)                            
    #print("Erreur dans la requête. Message d'erreur : " + str(e))
    return False, var


#################################################################### Apache SOLR functions (Europanea corpus freq)
def get_SOLR_collection_info(solr_host,solr_collection):
    ''' get solr collection info with pysolr'''
    try:
        solr = pysolr.Solr(solr_host+ solr_collection, search_handler='/schema/fields', use_qt_param=False)
        resp = solr._send_request('get', '/schema/fields')
        #print(resp)
        json_resp = json.loads(resp)
        #print(json_resp)
        for field in json_resp['fields']:
            print(field['name'], field['type'])
            if 'multiValued' in field:
                print('multiValued')
    except Exception as e:
        print("Error searching schema info -  Apache Solr :" + str(e))
    
def query_solr(solr, query, params):
   '''
   Query Solr with given query and parameters
   '''
   try:
       res = solr.search(query, **params)
       #print(res)
       return res
   except Exception as e:
        print("Error updating document to Apache Solr :" + str(e))
        return False

def query_solr_all_results(solr,query, params):
    totalres = []
    totalhl={}
    # first check number of results (<50 == discard)
    done = False
    while done is False:
        results = query_solr(solr, query, params)
        #print(params['cursorMark'], ' / ', results.hits)
        #exit()
        for doc in results.docs:
            totalres.append(doc)
        totalhl.update(results.highlighting)
        #for doc in results.highlighting:
        #    totalhl.append(doc)
        if params['cursorMark'] == results.nextCursorMark:
            done = True
        params['cursorMark'] = results.nextCursorMark
    return totalres, totalhl


#####################################################################  MYSQL Save functions
# to add alter table wiktionary_lexicon drop primary key, add primary key(`language`,`word_lemma`,`part_of_speech`);  
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
                                       autocommit=True,
                                       charset='utf8')
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
                try:
                    cursor.execute(mysql_cmd + table + """ (word_lemma,language,main_morph,freq_c1,freq_c2,part_of_speech)
                        VALUES (%(word_lemma)s,%(language)s,%(word_lemma)s,%(freq_c1)s,%(freq_c2)s,%(part_of_speech)s) ON DUPLICATE KEY UPDATE
                        freq_c1="%(freq_c1)s", freq_c2="%(freq_c2)s" """, row)
                    conn.commit()
                    warning = cursor.fetchwarnings()
                    if warning:
                        warnings.append({str(warning) : row})
                except Exception as e:
                    var = traceback.format_exc()
                    print("Error in : def save_lexies_to_mysql(table, data):. Error : \n" + var) 
                    #exit()                           
                    
            return True, warnings
        else:
            return False, "Connection to the server error"
    except Exception as e:
        var = traceback.format_exc()
        print("Error in : def save_lexies_to_mysql(table, data):. Error : \n" + var)                            
        return False, var

def update_lexies_def_to_mysql(table, words, data, lang, debug=False):
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
                                       autocommit=True,
                                       charset='utf8')
        if conn.is_connected():
            #print('Connected to Mysql database' + "\n")
            cursor = conn.cursor()
            # Enforce UTF-8 for the connection.
            cursor.execute('SET NAMES utf8mb4')
            cursor.execute("SET CHARACTER SET utf8mb4")
            cursor.execute("SET character_set_connection=utf8mb4")

            for elt in data:
                definition =  re.sub('"', "'", data[elt])
                definition =  re.sub(r"\[\]", "", definition) + "<a href='https://fr.wiktionary.org/wiki/" + re.sub(" ","_",elt) + "' target='new'><i class='fa fa-external-link' style='color:blue;'></i></a>"
                if debug:
                    print(elt)
                q = "UPDATE " + table + ' SET definition="' + definition + '" where word_lemma="' + elt + '" and language="'+lang_corresp[lang]+'" and part_of_speech="'+pos_corresp[words[elt]]+'";'
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

#####################################################################  Functions to get frequency for words


def get_word_frequency_solr(solr_collection,words):
    # test solr
    solr =  pysolr.Solr(solr_collections[solr_collection]+ solr_collection, always_commit=True)
    try : 
        solr.ping()
    except Exception as e:
        print("Problem with Apache Solr Server. Check error message : " + str(e) + "\nURL :" + solr_collections[solr_collection]+ solr_collection)
        exit()
    
    fout =  open(solr_collection + '.word_counts.csv', mode="w")
    fout.write("word,count\n")
    for word in words:
            params = {'rows':1}
            query = 'contents:'+word
            res = query_solr(solr, query, params)
            if res:
                #print(res.hits)
                fout.write(word + ',' + str(res.hits) + "\n")
    fout.close()


def read_frequency_file(fn, col_nb=2):
    res = {}
    with open(fn) as fout:
        for line in fout:
            data=line.strip().split(",")
            if len(data)==col_nb:
                try:
                    res[data[0]]= int(data[col_nb-1])
                except Exception as e:
                    print("Error on this line : " + str(data) + ". Error : " + str(e))
            else:
                print("Bad line : " + str(data) + ". Skipping")
    return res
############################################################################# main
####### tasks specification

#tasks = ['all','lexies','lexies_freq_update','lexies_def_update','europanea_freq','jsi_freq']
tasks = ['all'] #,'jsi_contexts'
# solr Collections
solr_collections = {'europaena_news':'https://tal.lipn.univ-paris13.fr/solr8/','rss_french':'https://tal.lipn.univ-paris13.fr/solr/'}
#################### load polysemic words

words = {}
words_sense = {}
print("loading words")
with open("liste_words_def_light.txt") as f:
    for line in f:
        data = line.split("\t")
        if len(data)==3 and re.match(r"\w{4,}$", data[0]): # just keep simple words (no hyphen or blank)
            words[data[0]]= data[1]
            words_sense[data[0]]= data[2].strip()
        else:
            print('unable to parse this line :' + line)
print(str(len(words)), " words loaded")

lang='fr'
pos_corresp={'N':'8','V':'15', 'ADJ':'1'}
lang_corresp={'fr':'1'}

# save lexies counts and other information for all words
if 'jsi_freq' in tasks or 'all' in tasks:
    print("Generating word frequency from rss_french collection")
    if os.path.isfile('rss_french.word_counts.csv') is False:
        get_word_frequency_solr('rss_french', words)
        
if 'all' in tasks or  'europaena_freq' in tasks:
    print("Generating word frequency from europaena_news collection")
    if os.path.isfile('europaena_news.word_counts.csv') is False:
        get_word_frequency_solr('europaena_news',words)

# insert or update lexies
if 'all' in tasks or 'lexies' in tasks:
    print("Storing lexemes into mysql db")
    lexies=[]
    # read frequencies
    eur_file = 'europaena_news.word_counts.csv'
    jsi_file = 'rss_french.word_counts.csv'
    if os.path.isfile(eur_file) is False:
        print("You need first to generate frequency file [" + eur_file + "]. Task : europanea_freq")
        exit()
    eur_freq = read_frequency_file(eur_file, col_nb=2)
    if os.path.isfile(jsi_file) is False:
        print("You need first to generate frequency file [" + jsi_file + "]. Task : jsi_freq")
        exit()
    jsi_freq = read_frequency_file(jsi_file, col_nb=2)
    #print(jsi_freq)
    #exit()
    for w in words.keys():
        print("parsing : " + w)
        freq_c2 = jsi_freq.get(w,0)
        freq_c1 = eur_freq.get(w,0)
        lexies.append({'word_lemma':w,'freq_c1':freq_c1,'freq_c2':freq_c2,'language':lang_corresp[lang],'part_of_speech':pos_corresp[words[w]]})

    print(len(lexies))
    #exit()
    res, detail = save_lexies_to_mysql('wiktionary_lexicon',lexies, ignore=False)
    if res:
        print("All is done for task : lexies")
        print("Warnings  (saved in ./logs/save_lexies_to_mysql_wiktionary_lexicon.json): ", detail)
        json.dump(detail,open('./logs/save_lexies_to_mysql_wiktionary_lexicon.json',mode="w"), indent=4)
    else:
        print("error in save_lexies_to_mysql('wiktionary_lexicon',lexies) function.", detail)
        exit()
#exit()
# update wiktionary definitions
if 'all' in tasks or 'lexies_def_update' in tasks:
    print("Storing lexeme definitions into mysql db")
    ## save wiktionary definitions
    res, detail = update_lexies_def_to_mysql('wiktionary_lexicon', words, words_sense, lang, debug=False)
    if res:
        print("All is done for lexies_def_update")
    else:
        print("error in update_lexies_def_to_mysql('lexies', words_sense) function.", detail)
        exit()

# update wiktionary definitions from frequency files (overall corpus not from kept sentences in sentences2 table)
if 'lexies_freq_update' in tasks:
    # build data for update from frequency files
    # read frequencies
    eur_file = 'wiktionary.europanea.word_counts.csv'
    jsi_file = 'wiktionary.jsi.word_counts.csv'
    if os.path.isfile(eur_file) is False:
        print("You need first to generate frequency file [" + eur_file + "]. Task : europanea_freq")
        exit()
    eur_freq = pd.read_csv(eur_file).set_index('word').to_dict()
    #print(eur_freq)
    if os.path.isfile(jsi_file) is False:
        print("You need first to generate frequency file [" + jsi_file + "]. Task : jsi_freq")
        exit()
    jsi_freq = pd.read_csv(jsi_file).set_index('word').to_dict()
    #print(jsi_freq)
    freqs = {k: [eur_freq.get(k, 0), jsi_freq.get(k, 0)] for k in set(eur_freq.keys()).union(set(jsi_freq.keys()))}

    ## save wiktionary definitions
    res, detail = update_lexies_freq_to_mysql('wiktionary_lexicon', freqs)
    if res:
        print("All is done for lexies_def_update")
    else:
        print("error in update_lexies_def_to_mysql('lexies', words_sense) function.", detail)
        exit()
