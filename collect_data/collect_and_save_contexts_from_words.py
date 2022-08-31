# this program read an external file (filled by the web platform, when people asked for contexts) with one word,pos per line
# and do the following :
# 1. retrieve JSI and Europanea overall frequency and contexts (limited to 10000 each, as stated in the config file), and save them to a mysql db () evolsem.sentences2 mysql table 
# and update frequency in evolsem.lexies (or wiktionary_lexicon)

import logging
log = logging.getLogger(__name__)
import configparser
import sys, os, re
import time
from glob import glob
import traceback
import numpy as np
import pandas as pd
 # solr functions
import pysolr, json, requests

# see https://dev.mysql.com/doc/connector-python/en/  
import mysql.connector
from mysql.connector import Error


#################################################################### SketchEngine functions (JSI corpus)
# paramètres sketchengine
USERNAME = 'ecartierdijon21000'
API_KEY = '8627c3386edb448383fb30d5999d3334'

#USERNAME = 'ecartierlipn'
#API_KEY = 'baba4579828d497fb3bd64613a8db4fe'
base_url = 'https://api.sketchengine.eu/bonito/run.cgi'

# ## generic paramteters for sketchengine API query (view query)
params = {
 'format': 'json', # format de la réponse (attention au 30/03/2020 : métainformations disponibles seulement avec json!)
 'async':0, # mode de réponse (ici on récupère toute la réponse, c'est plus long mais plus facile à gérer)
 'corpname': 'preloaded/fra_jsi_newsfeed_virt',# corpus
 'attrs': 'word,lemma,tag', # informations pour le mot clé
 'ctxattrs': 'word,lemma,tag', # idem pour les mots du contexte
 'structs':'date,uri,source_country,website',# meta-informations (voir résultats requête précédente corp_info)
 'refs':'=doc.uri,=doc.website,=doc.date,=doc.source_country',
 'viewmode':'sen', # on récupère le mode sentence (phrase vs kwic)
 'pagesize':1, # nbre de résultats maximum
}


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
    return True, res
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
                try:
                    cursor.execute("INSERT IGNORE INTO " + table + """ (word,pos,key_word,corpus,journal,url,date,sentence)
                        VALUES (%(word)s,%(pos)s,%(key_word)s,%(corpus)s,%(journal)s,%(url)s,%(date)s,%(sentence)s)""", row)
                    conn.commit() 
                except Exception as e:
                    var = traceback.format_exc()
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

######################################################################### main functions
def read_inputfile(fn):
    ''' Read input file with one word per line and return word list'''
    words = {}
    #pos_corresp={'N':8,'V':15}
    with open(fn) as file_in:
        for line in file_in:
            data = line.strip().split(',')
            if len(data)==2:
                if re.search(r"\.\?", data[0]):
                    w = re.sub(r"\.\?"," ", data[0])
                    words[w]=data[1]
                else:
                    words[data[0]]=data[1]
            else:
                log.error("Problem with reading this line : " + line)
    return words

# Europanea
def retrieve_word_frequency_europanea(word, start_date=1880, period=40):
    global error_words
    params = {'rows':1,'fq': 'date:['+str(start_date)+'-01-01T00:00:00Z TO ' + str(start_date+period) + '-01-01T00:00:00Z]'}
    if re.search(r" ",word):
        query = 'contents:"' + word + '"'
    else:
        query = 'contents:'+word
    try:
        res = query_solr(solr, query, params)
        if res:
            #print(res.hits)
            log.info(word + ',' + str(start_date)+'-'+str(start_date+period) + ',' + str(res.hits) + "\n")
            return True, res.hits
    except Exception as e:
        var = traceback.format_exc()
        log.error("Error in : retrieve_eur_contexts. Error : \n" + var)
        error_words[word]=var
        return False, var

def retrieve_eur_contexts(word, outputdir, start_date=1880, period=40):
    ''' Retrieve EUR contexts for given word and save to a file'''
    global error_words
    word = word.strip()
    fout = outputdir + word+'.' + str(start_date) + '-' + str(start_date+period) +'.json'
    if os.path.isfile(fout):
        log.info("already retrieved. Skipping. (" + fout +')')
        return True, fout
        
    params = {'sort':'id asc',
			'rows':50,
            'fq': 'date:['+str(start_date)+'-01-01T00:00:00Z TO ' + str(start_date+period) + '-01-01T00:00:00Z]',
			'cursorMark':'*',
			'fl':'source,date,id',
			"hl.method":"unified",
			"hl.snippets": "2",
			"hl": "true",
			"hl.simple.post": "</mark>",
			"hl.fragsize": "120",
			"hl.fl": "contents", 
			"hl.simple.pre": "<mark>"
	}
    log.info("retrieving data for : " + word + ", " + str(start_date) + "-" + str(start_date+period))        
    if re.search(r" ",word):
        query = 'contents:"' + word + '"'
    else:
        query = 'contents:'+word

    try:
        docs, hl = query_solr_all_results(solr,query, params)
        res=[]
        if docs:
            for doc in docs:
                if doc['id'] in hl:
                    for s in  hl[doc['id']]['contents']:
                        if re.search(word, s, re.I):
                            doc['hl'] = s
                            res.append(doc)                            
            json.dump(res, open(fout, mode='w'), indent=4)
            log.info("Data stored in " + fout)
            return True, fout
        else:
            log.info("Error with this word contexts retrieval (no results)" + word)
            return False,''
    except Exception as e:
        var = traceback.format_exc()
        log.error("Error in : retrieve_eur_contexts. Error : \n" + var)
        error_words[word]=var
        return False, var

def prepare_eur_contexts_and_save_to_mysql(w,cat, filename):
        global error_words
        try:
            # pas de filtrage en bbre car très bruité
            dftmp = pd.read_json(filename,orient='records')
            print("parsing : " + w, dftmp.shape[0], ' initial entries')
            if dftmp.shape[0]>10000:
                df = dftmp.sample(n=10000, random_state=5)
            else:
                df = dftmp.copy()
            df.rename(columns={'id':'url','hl':'sentence','source':'journal'}, inplace=True)
            df['corpus']='europanea'
            df['word']=w
            df['pos']=cat
            df['sentence'] = df['sentence'].astype(str)
            df['key_word'] = df['sentence'].str.extract(r"<mark>(.+?)<\/mark>",expand=True)
            df = df[df['key_word'].str.fullmatch(w[:-1] + "..?.?",case=False)]
            df['sentence'].replace(to_replace="[\[\]]", value="", regex=True, inplace=True)  
            df['date']= df['date'].dt.strftime('%Y-%m-%d')
            res, detail = save_sentences_to_mysql('sentences2', df.to_dict(orient='records'), debug=True)
            if res == False:
                log.info("error in save_sentences_to_mysql('sentences2', df.to_dict(orient='records'), debug=True) function.", detail)
                exit()

        except Exception as e:
            var = traceback.format_exc()
            log.error("Error in : def 'europanea_contexts' task, word=" + w + " Error : \n" + var) 
            error_words[w]=var

# JSI
def retrieve_word_frequency_jsi(word):
    global error_words
    word = word.strip()
    words = re.split("\s+",word)
    q = 'q'
    for w in words:
        q = q + '[lemma_lc="'+w+'"]'
    #params['q'] = 'q[lemma_lc="'+word+'"]' # la requête
    params['q'] = q # la requête
    try:
        res, detail = query_sketchengine(params,'view') # view = concordance
        if res:	
            if 'concsize' in detail:
                return True, detail['concsize']
            else:
                log.error("No results for this word : " + word + ', error : ' + str(res))
    except Exception as e:
        var = traceback.format_exc()
        log.error("Error in : retrieve_word_frequency_jsi. Error : \n" + var)
        error_words[word]=var
        return False, var

# merge contexts files (called from retrieve_jsi_contexts)
def jsi_merge_files(w,corpus,files,outputdir):
    fout = outputdir + corpus + '.' + w + '.csv'
    data = []
    for file in files:
        try:
            with open(file) as f:
                datatmp = json.loads(f.read())
                if len(datatmp['Lines'])==0:
                    continue
                for lines in datatmp['Lines']:
                    res = {}
                    res['url']= lines['Refs'][0]
                    res['website']= lines['Refs'][1]
                    res['date']= lines['Refs'][2]
                    res['country']= lines['Refs'][3]
                    res['left_context'] = [lines['Left'][i]['str'] for i in range(0,len(lines['Left']))]
                    res['keyword'] = lines['Kwic'][0]['str'] + lines['Kwic'][1]['str']
                    res['right_context'] = [ lines['Right'][i]['str'] for i in range(0,len(lines['Right']))]
                    data.append(res)
        except Exception as e:
            var = traceback.format_exc()
            log.error("Error in : def 'jsi_merge_files'. Error : \n" + var) 
            continue                           
    try:   
        log.info(str(len(data)) +  " occurrences")
        df = pd.DataFrame(data)
        if df.shape[0]> 0:
            log.info(df.info())
            df.to_csv(fout, index=False)
            log.info("Deleting source files")
            for fn in files:
                os.remove(fn)
            return True, fout
        else:
            return False, "No data"
    except Exception as e:
        var = traceback.format_exc()
        log.error("Error in : def 'jsi_merge_files'. Error : \n" + var) 
        return False, var                           

def retrieve_jsi_contexts(w,outputdir, freq):
    ''' Retrieve JSI contexts for given words and save to a file'''
    global error_words
    cmd = 'view' # concordance search
    w = w.strip()
    w2 = re.sub("\s+","_",w)
    corpus = params['corpname'].split("/")[1]
    fout = outputdir + corpus + '.' + w2 + '.csv'
    # check if file already generated
    if os.path.isfile(fout):
        log.info("already generated file for " + w + " (" + fout + "). Skipping.")
        return True, fout
    # search list of files in case several results (per year or month)
    files = glob(outputdir + corpus + '.*.' + w2 + '.csv')
    if len(files) > 0:
        res, fout = jsi_merge_files(w,corpus,files,outputdir)
        if res:
            return True, fout
        else:
            log.error("Error while merging result files : " + str(fout))
            error_words[w] = fout
            return False, fout

    # build query
    word_comps = re.split("\s+",w)
    q = ''
    for w in word_comps:
        q += '[lemma_lc="' + w + '"]'
    q = 'q'+q
    log.info("query : " + q)
    params['q'] = q # la requête
    try:
        if freq>10000: # per year
            for year in ('2014','2015','2016','2017','2018','2019','2020','2021'):
                params['pagesize']=1500
                params['q']=   q + ' within <doc (year="' + year +'") />'
                filename = outputdir + corpus + '.'+ year + '.' + w2 + '.' + params['format']
                if os.path.isfile(filename)==False:
                    log.info("Querying " + year + ' corpus')
                    time.sleep(2)
                    truefalse,res = query_sketchengine(params,cmd)
                    if truefalse:
                        with open(filename, mode="w", encoding="utf-8") as fin:
                            if params['format']=='json':
                                json.dump(res,fin, indent=4)
                            elif params['format'] == 'csv':
                                fin.write(res.text)
                        log.info("Stockage des résultats dans :" +  filename)
                else:
                    log.info(filename + " already retrieved. Skipping.")
                    continue
            # merge files
            files = glob(outputdir + corpus + '.*.' + w2 + '.' + params['format'])
            log.info(str(len(files)) + " to parse")
            if len(files) > 0:
                res, fout = jsi_merge_files(w,corpus,files,outputdir)
                if res:
                    return True, fout
                else:
                    log.error("Error while merging result files : " + str(fout))
                    error_words[w] = fout
                    return False, fout
            else:
                log.error("No file to parse. perhaps you need to check the files pattern")
                error_words[w] = fout
                return False, fout

        else: # overall search
            params['pagesize']=10000
            params['q']=   q
            time.sleep(2)
            truefalse,res = query_sketchengine(params,cmd)
            if truefalse:
                with open(fout, mode="w", encoding="utf-8") as fin:
                    if params['format']=='json':
                        json.dump(res,fin, indent=4)
                    elif params['format'] == 'csv':
                        fin.write(res.text)
                log.info("Stockage des résultats dans :" +  fout)
                return True, fout
            else:
                log.error(fout + " Contexts not retrieved.")
                error_words[w] = res
                return False, res
    except Exception as e:
        var = traceback.format_exc()
        log.error("Error in : def 'query_sketchengine'. Error : \n" + var) 
        error_words[w] = res
        return False, var                           

def generate_jsi_complete_file(word, filein):
    global error_words
    word = word.strip()
    fout = filein + '.complete.csv'
    if os.path.isfile(fout):
        log.info("Complete file already generated. Skipping.")
        return True, fout
    try:
        df = pd.read_csv(filein,error_bad_lines=False)
    except:
        var = traceback.format_exc()
        log.error("Error in : def 'generate_jsi_complete_file'. Error : \n" + var) 
        error_words[word] = var
        return False, var                           
    try:
        # on ajoute les données temporelles (pour l'année)
        df['datetime'] = pd.to_datetime(df['date'], infer_datetime_format=True)
        df['year'] = df['datetime'].dt.strftime('%Y')
        # nettoyage initial : si la colonne keyword ne contient pas le mot, pb antérieur de parsing ... 
        # on les enlève (en fait il faudrait régler le problème en amont)
        count = df[~df.keyword.str.contains(word, flags=re.I)].shape[0]
        if count > 0:
            log.warning("Nb lignes sans le mot -clé : " + str(count))
            log.warning(df[~df.keyword.str.contains(word)].keyword.value_counts())
            #df = df[df.keyword.str.contains(word)]

        # first step : transform list as string to list
        df["left_context"] = df["left_context"].apply(eval)
        df["right_context"] = df["right_context"].apply(eval)

        # on crée une colonne sentence avec la phrase initiale
        df['sentence'] = df["left_context"].str[0::2].str.join(' ') + ' ' + df['keyword'].str.replace(r"/.+$",'', regex=True) + ' ' +df["right_context"].str[0::2].str.join(' ')
        df.sentence.value_counts().head(3)

        # on crée des colonnes pour le "mot-clé" (avec forme, lemme et pos)
        df[['kw','kw_lemma','kw_pos']] = df.keyword.str.split("/", expand=True)
        #df['kw_lemma'] = df.kw_lemma.str.lower()
        df['kw_lemma'] = df.kw_lemma.str.strip()
        df['kw_pos'] = df.kw_pos.str.lower()
        df['kw_pos'] = df.kw_pos.str.strip()
        #df['kw'] = df.kw.str.lower()
        df['kw'] = df.kw.str.strip()

        # attention : si récup manuelle,  l'ordre forme lemme pos est inversé....
        #df['kw_pos'],df['kw_lemma']=np.where(df['kw_pos'].str.contains(word),(df['kw_lemma'].str.lower(),df['kw_pos']),(df['kw_pos'],df['kw_lemma']))

        # first extract 5 words on the left and on the right

        ############ left word/lemma/pos
        df['left_w1'] = df['left_context'].str[-2].str.strip()
        df['left_lp1'] = df['left_context'].str[-1].str.strip()
        df[['left_l1','left_p1']] = df['left_lp1'].str.extract(r"^/([^/]+)/(.+)$", expand = True)
        #print(df.left_w1.value_counts().head(20))
        #print(df.left_p1.value_counts().head(20))
        #print(df.left_l1.value_counts().head(20))

        ######### word2
        df['left_w2'] = df['left_context'].str[-4].str.strip()
        df['left_lp2'] = df['left_context'].str[-3].str.strip()
        df[['left_l2','left_p2']] = df['left_lp2'].str.extract(r"^/([^/]+)/(.+)$", expand = True)

        ######### word3
        df['left_w3'] = df['left_context'].str[-6].str.strip()
        df['left_lp3'] = df['left_context'].str[-5].str.strip()
        df[['left_l3','left_p3']] = df['left_lp3'].str.extract(r"^/([^/]+)/(.+)$", expand = True)

        ######### word4
        df['left_w4'] = df['left_context'].str[-8].str.strip()
        df['left_lp4'] = df['left_context'].str[-7].str.strip()
        df[['left_l4','left_p4']] = df['left_lp4'].str.extract(r"^/([^/]+)/(.+)$", expand = True)

        ######### word5
        df['left_w5'] = df['left_context'].str[-10].str.strip()
        df['left_lp5'] = df['left_context'].str[-9].str.strip()
        df[['left_l5','left_p5']] = df['left_lp5'].str.extract(r"^/([^/]+)/(.+)$", expand = True)

        #print(df.left_w1.value_counts().head(20))
        # the same with right context
        # first extract 5 words on the right and on the right

        ############ right word/lemma/pos
        df['right_w1'] = df['right_context'].str[0].str.strip()
        df['right_lp1'] = df['right_context'].str[1].str.strip()
        df[['right_l1','right_p1']] = df['right_lp1'].str.extract(r"^/([^/]+)/(.+)$", expand = True)
            #print(df.right_w1.value_counts().head(20))
            #print(df.right_p1.value_counts().head(20))
            #print(df.right_l1.value_counts().head(20))

        ######### word2
        df['right_w2'] = df['right_context'].str[2].str.strip()
        df['right_lp2'] = df['right_context'].str[3].str.strip()
        df[['right_l2','right_p2']] = df['right_lp2'].str.extract(r"^/([^/]+)/(.+)$", expand = True)

        ######### word3
        df['right_w3'] = df['right_context'].str[4].str.strip()
        df['right_lp3'] = df['right_context'].str[5].str.strip()
        df[['right_l3','right_p3']] = df['right_lp3'].str.extract(r"^/([^/]+)/(.+)$", expand = True)

        ######### word4
        df['right_w4'] = df['right_context'].str[6].str.strip()
        df['right_lp4'] = df['right_context'].str[7].str.strip()
        df[['right_l4','right_p4']] = df['right_lp4'].str.extract(r"^/([^/]+)/(.+)$", expand = True)

        ######### word5
        df['right_w5'] = df['right_context'].str[8].str.strip()
        df['right_lp5'] = df['right_context'].str[9].str.strip()
        df[['right_l5','right_p5']] = df['right_lp5'].str.extract(r"^/([^/]+)/(.+)$", expand = True)

        #print(df.right_w1.value_counts().head(20))
        #print(df.right_p1.value_counts())
        reduce_pos={'DET:ART':'DET', 'KON':'CONJ', 'PRP:det':'PRP_DET', 'VER:pper':'PP_ADJ', 'VER:pres':'VER', 'VER:infi':'VER', 'VER:futu':'VER', 'VER:simp':'VER', 'DET:POS':'DET', 'PRO:DEM':'DET', 'VER:ppre':'VER', 'VER:subi':'VER', 'VER:subp':'VER', 'VER:impf':'VER'}
        df['left_p1'] = df['left_p1'].replace(reduce_pos)
        df['left_p2'] = df['left_p2'].replace(reduce_pos)
        df['left_p3'] = df['left_p3'].replace(reduce_pos)
        df['left_p4'] = df['left_p4'].replace(reduce_pos)
        df['left_p5'] = df['left_p5'].replace(reduce_pos)
        df['right_p1'] = df['right_p1'].replace(reduce_pos)
        df['right_p2'] = df['right_p2'].replace(reduce_pos)
        df['right_p3'] = df['right_p3'].replace(reduce_pos)
        df['right_p4'] = df['right_p4'].replace(reduce_pos)
        df['right_p5'] = df['right_p5'].replace(reduce_pos)
            
        df.drop(columns=['left_context','right_context','left_lp1','left_lp2','left_lp3','left_lp4','left_lp5','right_lp1','right_lp2','right_lp3','right_lp4','right_lp5'], inplace=True)
        df.drop_duplicates(subset=['sentence'], inplace=True)
        df.to_csv(fout, index=False)
        return True, fout
    except Exception as e:
        var = traceback.format_exc()
        log.error("Error in : def 'generate_jsi_complete_file'. Error : \n" + var) 
        error_words[word] = var
        return False, var                           

def save_jsi_contexts_to_mysql(word, cat, filein):
    global error_words
    #print(word, cat,filein)
    try:
        df = pd.read_csv(filein,error_bad_lines=False)
        #print(df.shape)
        if df.shape[0]==0:
            log.error("No data in this file : " + filein)
            error_words[word]= "no data in complete file" + filein
            return False, "no data in complete file" + filein
        else:
            df.rename(columns={'id':'url','hl':'sentence','website':'journal','kw':'key_word'}, inplace=True)
            df['corpus']='jsi'
            df['word']=word
            df['pos']=cat
            df['sentence'] = df.apply(lambda x : x['sentence'].replace(x['key_word'],"<mark><b>" + x['key_word'] + "</b></mark>"),1)    
            #df['sentence'] = df['sentence'].str.replace(df['key_word'].str.value, "<mark><b>" + df['key_word'].str.value + "</b></mark>")
            res, detail = save_sentences_to_mysql('sentences2', df.to_dict(orient='records'))
            if res == False:
                log.error("error in save_sentences_to_mysql('sentences2', df.to_dict(orient='records')) function.", detail)
                error_words[word] = "Error in saving into db. Error : " + str(detail)
                return False, "Error in saving into db. Error : " + str(detail)
            else:
                return True, "Contexts saved"

    except Exception as e:
        var = traceback.format_exc()
        log.error("Error in : def 'save_jsi_contexts_to_mysql' task. Error : \n" + var)                            
        error_words[word]=var 
        return False, var                          



############################################# main
######################## Solr paramaters
# Apache Solr parameters
solr_host = 'https://tal.lipn.univ-paris13.fr/solr8/'
solr_collection = 'europaena_news'
solr =  pysolr.Solr(solr_host+ solr_collection, always_commit=True)

def ping_solr():
    try : 
        solr.ping()
        return True, ""
    except Exception as e:
        var = traceback.format_exc()
        print("Problem with Apache Solr Server. Error : \n" + var)  
        return False, var                          
        #print("Problem with Apache Solr Server. Check error message : " + str(e))
        #exit()

# mysql connection parameters
host = 'localhost'
user = 'root'
password = 'neoveille'
db = 'evolsem'

def main():
    if len(sys.argv) != 2:
        print("You need to specify the input filename containing word, cat data list to parse. Retry.")
        exit()
    global error_words
    error_words={}
    error_file1 = './log/europanea.word.errors.json'
    start_date = 1880
    period = 40
    # read external file with words
    wordinputfile = sys.argv[1]
    words = read_inputfile(wordinputfile)
    log.info(words)
    # Europanea corpus
    print("*"*10,"Europanea corpus")
    for word in words:
        print("parsing : " + word)
        print("generating frequency")
        res, msg = ping_solr()
        if res is False:
            res1=False
            freq1=msg
        else:
            res1, freq1 = retrieve_word_frequency_europanea(word, start_date, period)
        if res1 is False:
            print("error with word frequency retrieval. Reason :" + str(freq1))
            freq1 = 10000
        else :
            print("overall frequency : " + str(freq1))
            update_lexies_corpus_freq_to_mysql("wiktionary_lexicon", word, str(freq1), "eur")
        print("retrieving contexts")        
        res2, fout = retrieve_eur_contexts(word, outputdir, start_date, period)
        if res2:
            print("Saving contextes")        
            prepare_eur_contexts_and_save_to_mysql(word,words[word], fout)
        else:
            print("error with word contexts retrieval. Reason :" + str(fout))
        #else: 
        #    print("error with word frequency. Reason :" + str(freq1))
    if len(error_words)> 0:
        print('All is done for Europanea. Check error file (words are rewritten into input file) : ' + error_file1)
        json.dump(error_words, open(error_file1, mode='w'))
    else:
        print("All is done for Europanea. No errors.")
        if os.path.isfile(error_file1):
            os.remove(error_file1)
    
    # JSI corpus
    error_file2 = './log/jsi.word.errors.json'
    print("*"*10,"JSI corpus")
    for word in words:
        print("parsing : " + word)
        print("generating frequency")
        res1, freq2 = retrieve_word_frequency_jsi(word)
        if res1:
            print("overall frequency : " + str(freq2))
            update_lexies_corpus_freq_to_mysql("wiktionary_lexicon", word, str(freq2), "jsi")
            print("retrieving contexts")        
            res2, fout = retrieve_jsi_contexts(word, outputdir,freq2)
            if res2:
                print("Generating complete file before saving into db")
                res3, fout = generate_jsi_complete_file(word, fout)
                if res3:
                    print("Saving complete file into db")
                    res4, fout = save_jsi_contexts_to_mysql(word, words[word], fout)
                    if res4:
                        print("All is done for this word" + word)
                    else:
                        print("Error with saving contexts into db. Reason : " + str(fout))
                else:
                    print("error with generating complete file. Reason : " + str(fout))
            else:
                print("error with word contexts retrieval. Reason :" + str(fout))
        else: 
            print("error with word frequency. Reason :" + str(freq1))
    if len(error_words)> 0:
        print('All is done for JSI. Check error file (words are rewritten into input file) : ' + error_file2)
        json.dump(error_words, open(error_file2, mode='w'))
    else:
        print("All is done for JSI. No errors.")
        if os.path.isfile(error_file2):
            os.remove(error_file2)

    # update frequency for eur and jsi into lexies table

    # update input file with words with errors (ie not saved in db)
    file_errors ={}
    if os.path.isfile(error_file1):
        file_errors = json.load(open(error_file1))
    if os.path.isfile(error_file2):
        jsi_errors = json.load(open(error_file2))
        file_errors.update(jsi_errors)
    with open(wordinputfile, mode="w") as fout:
        for w in file_errors:
            fout.write(w + "," + words[w] + "\n")



if __name__ == '__main__':
    if len(sys.argv)<2:
        print("Please indicate the word file as an argument! Exiting.")
        exit()
### with configfile to be done
#    if len(sys.argv)<2:
#        print("Please indicate the configuration file as an argument! Exiting.")
#        exit()
    #configfile = sys.argv[1]
    #print("reading configuration file :" + configfile)
    #config = configparser.ConfigParser()
    #config.read(configfile) 
    #outputdir = config['GENERAL']['outputdir']
    #logdir = config['GENERAL']['logdir']
    #corpora = config['GENERAL']['corpora'].split(',')
    #for corp in corpora:
    #    print(corp)
    #    print(config[corp+'_CONFIG'])
    #    for param in config[corp+'_CONFIG']:
    #        print(param, config[corp+'_CONFIG'][param])
    #params = json.loads(config.get("JSI_CONFIG","def_params"))
    #outputdir = config['GENERAL']['outputdir']
    #logdir = config['GENERAL']['logdir']
    #os.makedirs(logdir, exist_ok=True) # for logs
    #os.makedirs(outputdir, exist_ok=True) # for outputs  
    outputdir = './output/'
    logdir = './log/'
    os.makedirs(logdir, exist_ok=True) # for logs
    os.makedirs(outputdir, exist_ok=True) # for outputs  
    FORMAT = "%(levelname)s:%(asctime)s:%(message)s[%(filename)s:%(lineno)s - %(funcName)s()]"
    logging.basicConfig(format=FORMAT, datefmt='%m/%d/%Y %I:%M:%S %p', filename=logdir + os.path.basename(__file__) + ".log", filemode='w', level=logging.INFO) 
    main()
