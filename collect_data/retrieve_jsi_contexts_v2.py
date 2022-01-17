## Récupération contextes JSI pour les mots sélectionnés du wiktionnaire

# chargement des librairies nécessaires 
import requests, time, json, os, sys
import pandas as pd
import re
import os
import time
from glob import glob
import traceback

import logging
import logging.config

# mysql
import mysql.connector
from mysql.connector import Error
import traceback

# mysql connection parameters
host = 'localhost'
user = 'root'
password = 'neoveille'
db = 'evolsem'


# retrieve word list from mysql

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
    log.info("selecting fields into database/table : " + db + '.' + table + " . Fields : " + str(len(fields)))
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
            #log.info(q)
            cursor.execute(q)
            for row in cursor:
                #log.info(row)
                res[row[0]] = row[1]
            return True, res
        else:
            return False, "connection error"
    except Exception as e:
        var = traceback.format_exc()
        log.info("Error in : select_words_from_mysql. Error : \n" + var)                            
        if debug == True:
            exit()
        else:
            return False, var



# paramètres sketchengine (your username and api key)
USERNAME = ''
API_KEY = ''
base_url = 'https://api.sketchengine.eu/bonito/run.cgi'

# retrieve corpus info from sketchengine
def corpus_info(corpus):
	''' get corpus info'''
	params = {'gramrels':1, 'registry':1, 'struct_attr_stats':1,'subcorpora':1}
	params['corpname']=corpus
	res =  requests.get(base_url + '/corp_info', params=params, auth=(USERNAME, API_KEY)).json()
	if 'error' in res.keys():
		log.info("Error in result for query : [" + base_url + '/corp_info?], params : ' + str(params) + ', error : '+ res['error'])
		return False
	else :
		#log.info(res)
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
    log.error("Error in : def 'query_sketchengine'. Error : \n" + var)                            
    #print("Erreur dans la requête. Message d'erreur : " + str(e))
    return False, var


###################################### main
def main():
    tasks = ['corpus_info','retrieve_jsi_synthesis','retrieve_contexts','generate_synth_file','generate_complete_file','generate_website_file']
    tasks = ['context_embeddings']#,'retrieve_contexts','generate_synth_file','generate_complete_file'
    #input_dir = '/Volumes/Transcend/Evolsem_corpora/jsi/'
    output_dir = '/Volumes/Transcend/Evolsem_corpora/jsi/'
    #output_dir = './jsi_output/'
    check_dir = './jsi_output/'
    os.makedirs(output_dir, exist_ok=True)
    lang = 'fra'
    corpus = 'preloaded/fra_jsi_newsfeed_virt'
    ################################################# sketchengine query parameters
    # ## generic parameters for sketchengine API query
    params = {
    'format': 'json', # format de la réponse (attention au 30/03/2020 : métainformations disponibles seulement avec json!)
    'async':0, # mode de réponse (ici on récupère toute la réponse, c'est plus long mais plus facile à gérer)
    #'corpname': 'preloaded/frantext_trends',
    'attrs': 'word,lemma,tag', # informations pour le mot clé
    'ctxattrs': 'word,lemma,tag', # idem pour les mots du contexte
    #'q':'q[word="afro.+"]', # query
    'viewmode':'sen', # on récupère le mode sentence (phrase vs kwic)
    'pagesize':10000, # nbre de résultats maximum
    }
    cmd = 'view' # concordance search
    params['corpname']= corpus
    params['structs']='date,uri,source_country,website',# meta-informations (voir résultats requête précédente corp_info)
    params['refs']='=doc.uri,=doc.website,=doc.date,=doc.source_country'
    params['pagesize']=1
    corp_fn = params['corpname'].split('/')

    words = {}
    words_sense = {}


    ## get wordlist, either file, wikt, mysql
    from_wordlist='mysql'
    word_filter = [8] # ie noun, 15 for verb


    if from_wordlist=='file':
        try:
            with open('liste_candidats_verbes_vieilli.txt') as fin:
                for line in fin:
                    #print(line)
                    a =  re.search(r"^[\W]*?(\w+)_([0-9].+)", line)
                    if a:
                        #print(a.group(1))
                        #print(a.group(2))
                        w = a.group(1).strip()
                        words[w]="V"
                        words_sense[w] = words_sense.get(w,'') + "\n" + a.group(2).strip()

            with open('liste_candidats_noms_vieilli.txt') as fin:
                for line in fin:
                    a =  re.search(r"^[\W]*?(\w+)_([0-9].+)", line)
                    if a:
                        #print(a)
                        w = a.group(1).strip()
                        words[w]="N"
                        words_sense[w] = words_sense.get(w,'') + "\n" + a.group(2).strip()
        except Exception as e:
            var = traceback.format_exc()
            log.error("Error : " + var)
            print("Error : " + var)
            exit()

    elif from_wordlist == 'wikt':
        try:
            with open("../wiktionaire/liste_words_def_light.txt") as f:
                for line in f:
                    data = line.split("\t")
                    if len(data)==3:
                        words[data[0]]= data[1]
                        words_sense[data[0]]= data[2].strip()
                    else:
                        log.error('unable to parse this line :' + line)
        except Exception as e:
            var = traceback.format_exc()
            log.error("Error : " + var)
            print("Error : " + var)
            exit()
           
    elif from_wordlist=='mysql':
        log.info("retrieving word list from mysql")
        truefalse, wordlist = select_words_from_mysql()
        if word_filter and truefalse:
            words = {k:v for k,v in wordlist.items() if v in word_filter and re.match("[a-z]",k)}
        elif truefalse:
            words = {k:v for k,v in wordlist.items() if v in word_filter}
        else:
            log.error("No words retrieved. Check mysql query")
            print("No words retrieved. Check mysql query")
            exit()
   

    #words = {'réaliser':'réaliser'}
    #words_sense = {'réaliser':'réaliser'}
    log.info("Lauching processs with following paramaters\nTasks : " + str(tasks) + "\nWordlist : " +  str(words))
    print("*"*20 + "\nLauching processs with following paramaters\nTasks : " + str(tasks) + "\nWordlist : " +  str(words) +  "\n" + "*"*20)

    # get corpus info from sketchengine for relative frequency calculation
    if 'corpus_info' in tasks:
        outputdir = './jsi_output/'
        log.info("Task : corpus_info", ", check outputdir : " + outputdir)
        print("*"*10 + "Task : corpus_info"+ ", check outputdir : " + outputdir)
        os.makedirs(outputdir, exist_ok=True)
        corpora =  ['preloaded/fra_jsi_newsfeed_virt']# your corpora
        for corpname in corpora:
            corp_fn = corpname.split('/')
            res = corpus_info(corpname)
            if res:
            # sauvegarde dans fichier json dans l'environnnement
                with open(outputdir + corp_fn[1] + '.info.json', mode="w", encoding="utf-8") as fin:
                    json.dump(res,fin, indent=4)
                log.info("Réponse enregistrée dans : " + corp_fn[1] + '.info.json')

    # check number of results per word for each period and save it to file for future use
    if 'retrieve_jsi_synthesis' in tasks:
        error_words={}
        solr_collection = 'jsi-2014-2021'
        print("*"*10 + "Task : retrieve_jsi_synthesis", ", check outputdir : .")
        log.info("Task : retrieve_jsi_synthesis"+ ", check outputdir : .")
        if os.path.isfile(solr_collection + '.word_counts.csv') is False:
            fout =  open(solr_collection + '.word_counts.csv', mode="w")
            fout.write("word,period,count\n")
            for word in words:
                log.info("parsing " + word)
                word = word.strip()
                params['q'] = 'q[lemma_lc="'+word+'"]' # la requête
                time.sleep(2)
                res, detail = query_sketchengine(params,cmd) # view = concordance
                if res:	
                    if 'concsize' in res:
                        fout.write(word + ',' + str(res['concsize']) + "\n")
                else:
                    log.info("No results for this word : " + word)
                    error_words[word]=detail
                    continue
            if len(error_words)>0:
                json.dump(error_words,open('./logs/retrieve_jsi_synthesis.' + solr_collection + '.word_counts.csv.errors.json', mode='w'), indent=3)
                log.info("All is done. Check results in : [" + solr_collection + '.word_counts.csv]. Check errors in [./logs/retrieve_jsi_synthesis.' + solr_collection + '.word_counts.csv.errors.json]')
                error_words={}
            else:
                log.info("All is done. Check results in : " + solr_collection + '.word_counts.csv')


    ## retrieve contexts for each word and save it into a <corpus>.<word>.view.json file into outputdir 
    if 'retrieve_contexts' in tasks:
        log.info("Task : retrieve_contexts"+ ", check outputdir : .")
        print("*"*10 + "Task : retrieve_contexts"+ ", check outputdir : .")
        for n in words:
            n = n.strip()
            if re.search(r"\s",n):
                continue
            if os.path.isfile(check_dir + lang + '.' + n + '.csv'):
                log.info("already generated file for " + n + " (" + check_dir + lang + '.' + n + '.csv' +  "). Skipping.")
                files = glob(output_dir + corpus + '.' + n + '.view.json')
                for fn in files:
                    os.remove(fn)
                continue
            files = glob(output_dir + corp_fn[1] + '*.' + n + '.view.json')
            if len(files)>0:
                log.info("already retrieved for " + n + '. Skipping.')
                continue
            files = glob(output_dir + corp_fn[1] + '.' + n + '.view.json')
            if len(files)>0:
                log.info("already retrieved for " + n + '. Skipping.')
                continue

            log.info("Retrieving context for " + n)
            query_fn = n 
            params['q'] = 'q[lemma_lc="'+n+'"]' # la requête
            filename = output_dir + corp_fn[1] + '.' + query_fn + '.' + cmd + '.' + params['format']
            if os.path.isfile(filename)==True:
                log.info("Skipping this word, already retrieved : " + n + ':' +filename)
                continue
            time.sleep(5)
            try:
                res = query_sketchengine(params,cmd) # view = concordance
                if res:	
                    if 'concsize' in res and res['concsize']>1000000:
                        print(str(res['concsize']) + '=> year search')
                        for year in ('2014','2015','2016','2017','2018','2019','2020','2021'):
                            #params['usesubcorp']= subcorp + year
                            params['pagesize']=1
                            #params['pagesize']=10000
                            params['q']=   'q[lemma_lc="'+query_fn+'"]'+ 'within <doc (year="' + year +'") />'
                            filename = output_dir + corp_fn[1] + '.'+ year + '.' + query_fn + '.' + cmd + '.' + params['format']
                            if os.path.isfile(filename)==False:
                                log.info("Querying " + year + ' corpus')
                                time.sleep(5)
                                res = query_sketchengine(params,cmd)
                                if res:
                                    # if concsize > 10000 search by month
                                    if 'concsize' in res and res['concsize']>100000:
                                        print(str(res['concsize'])+ ' => month search')
                                        for month in ('01','02','03','04','05','06','07','08','09','10','11','12'):
                                            filename = output_dir + corp_fn[1] + '.'+ year + '.'+ month + '.' + query_fn + '.' + cmd + '.' + params['format']
                                            params['q']=   'q[lemma_lc="'+query_fn+'"]' + 'within <doc (month="' + year + '-' + month + '") />'
                                            if os.path.isfile(filename)==False:
                                                time.sleep(5)
                                                params['pagesize']=10000
                                                res = query_sketchengine(params,cmd)
                                                if res:
                                                    with open(filename, mode="w", encoding="utf-8") as fin:
                                                        if params['format']=='json':
                                                            json.dump(res,fin, indent=4)
                                                        elif params['format'] == 'csv':
                                                            fin.write(res.text)
                                                    print("Corpus utilisé : " + corp_fn[1] +  ", Requête :" + query_fn + ", Stockage des résultats dans :" +  filename)
                                            else:
                                                print(filename + " already retrieved. Skipping.")
                                    else:
                                        params['pagesize']=10000
                                        print(str(res['concsize'])+ " querying year corpus")
                                        time.sleep(5)
                                        res = query_sketchengine(params,cmd)
                                        with open(filename, mode="w", encoding="utf-8") as fin:
                                            if params['format']=='json':
                                                json.dump(res,fin, indent=4)
                                            elif params['format'] == 'csv':
                                                fin.write(res.text)
                                        log.info("Corpus utilisé : " + corp_fn[1] +  ", Requête :" + query_fn + ", Stockage des résultats dans :" +  filename)

                            else:
                                log.info(filename + " already retrieved. Skipping.")
                    
                    else:
                        print(str(res['concsize'])+ ' => overall search')
                        params['pagesize']=10000
                        filename = output_dir + corp_fn[1] + '.' + query_fn + '.' + cmd + '.' + params['format']
                        if os.path.isfile(filename)==False:
                            #print("Querying year corpus")
                            time.sleep(5)
                            res = query_sketchengine(params,cmd)
                            if res:
                                with open(filename, mode="w", encoding="utf-8") as fin:
                                    if params['format']=='json':
                                        json.dump(res,fin, indent=4)
                                    elif params['format'] == 'csv':
                                        fin.write(res.text)
                                log.info("Corpus utilisé : " + corp_fn[1] +  ", Requête :" + query_fn + ", Stockage des résultats dans :" +  filename)
                            else:
                                log.info("Problem with the last query. Please try again.")
                        else:
                            log.info(filename + " already retrieved. Skipping.")
            except Exception as e:
                var = traceback.format_exc()
                log.error("Error with the query : " + var)


    ## 'generate_synth_file' task
    #words = {'énoncer': 'V', 'tâcher': 'V', 'réciter': 'V', 'ouïr': 'V', 'défaillir': 'V', 'accéder': 'V', ' végéter': 'V', ' vaquer': 'V', ' trafiquer': 'V', ' toiser': 'V', ' répugner': 'V', ' meurtrir': 'V', ' glaner': 'V', ' divertir': 'V', ' agiter': 'V'}
    #print(len(words))

    if 'generate_synth_file' in tasks:
        output_dir = './jsi_output/'
        print("*"*10 + "Task : generate_synth_file", ", check outputdir : " + output_dir)
        log.info("Task : generate_synth_file"+ ", check outputdir : " + output_dir)
        #input_dir = './jsi_output/'
        input_dir = '/Volumes/Transcend/Evolsem_corpora/jsi/'
        corpus = 'fra_jsi_newsfeed_virt'
        lang='fra'
        missing = []
        for n in words:
            n = n.strip()
            n2 = re.sub(r"[àâäéèêëîïôöùûü]", '*',n)
            fn = output_dir + lang + '.' + n + '.csv'
            log.info("Parsing : " + n + "output file : "+ fn)
            if os.path.isfile(fn):
                log.info("already generated file for " + n + "(" + fn +  "). Skipping.")
                continue
            files = glob(input_dir + "*" + n2 + '.view.json')
            log.info(files)
            if len(files)==0:
                missing.append(n)
                log.info("No data for this word : " + n + '. Skipping.')
                continue
            #continue
            data = []
            for file in files:
                try:
                    with open(file) as f:
                        datatmp = json.loads(f.read())
                    #print(datatmp['Lines'][2])
                # reconstitue records (array of dictionary)
                    if len(datatmp['Lines'])==0:
                        continue
                    for lines in datatmp['Lines']:
                        res = {}
                        #print(lines['Refs'])
                        res['url']= lines['Refs'][0]
                        res['website']= lines['Refs'][1]
                        res['date']= lines['Refs'][2]
                        res['country']= lines['Refs'][3]
                        res['left_context'] = [lines['Left'][i]['str'] for i in range(0,len(lines['Left']))]
                        res['keyword'] = lines['Kwic'][0]['str'] + lines['Kwic'][1]['str']
                        res['right_context'] = [ lines['Right'][i]['str'] for i in range(0,len(lines['Right']))]
                        #res['sentence'] = " ".join(res['left_context'][0::2]) + " " +  lines['Kwic'][0]['str'] +  " ".join(res['right_context'][0::2])
                        #print(lines['Refs'],lines['Left'],lines['Kwic'],lines['Right'])
                        data.append(res)
                except Exception as e:
                    var = traceback.format_exc()
                    log.error('Error with this file ' + file + ". Error : \n" + var)
                    continue
            
            log.info(str(len(data)) +  " occurrences")
            df = pd.DataFrame(data)
            if df.shape[0]> 0:
                log.info(df.info())
                # ajout des données récupérées manuellement si elles existent
                files = glob(input_dir + lang + '.' + n + "*.manual_retrieval.csv")
                if len(files)==1:
                    df2 = pd.read_csv(files[0])
                    df3 = pd.concat([df2,df])
                    log.info(df3.info())
                    #df3.drop_duplicates(inplace=True)
                    #log.info(df3.info())
                    df3.to_csv(output_dir + lang + '.' + n + '.csv', index=False)
                else:
                    df.to_csv(output_dir + lang + '.' + n + '.csv', index=False)
                log.info("Deleting source files")
                for fn in files:
                    os.remove(fn)
            

        log.info("Missing files for words : " + str(missing))


    ## 'generate_complete_file' task
    # ## parse generated file in the preceding step and split information
    # ## generate a file per word in output_dir : lang + '.' + word +  '.complete.csv'
    # 


    if 'generate_complete_file' in tasks:
        input_dir ='./jsi_output/'
        print("*"*10 + "Task : generate_complete_file", ", check outputdir : " + input_dir)
        log.info("Task : generate_complete_file"+ ", check outputdir : " + input_dir)

        lang= 'fra'
        for word in words:
            word = word.strip()
            log.info("parsing word : " + word) 
            if os.path.isfile(input_dir + lang + '.' + word + '.complete.csv'):
                log.info("already parsed. Skipping.")
                continue
            try:
                df = pd.read_csv(input_dir + lang + '.' + word + '.csv')
            except:
                log.info("No file found for " + word + ". Skipping.")
                continue
            try:
                # on ajoute les données temporelles (pour l'année)
                df['datetime'] = pd.to_datetime(df['date'], infer_datetime_format=True)
                df['year'] = df['datetime'].dt.strftime('%Y')
                # nettoyage initial : si la colonne keyword ne contient pas le mot, pb antérieur de parsing ... 
                # on les enlève (en fait il faudrait régler le problème en amont)
                count = df[~df.keyword.str.contains(word, flags=re.I)].shape[0]
                if count > 0:
                    log.info("Nb lignes sans le mot -clé : " + str(count))
                    log.info(df[~df.keyword.str.contains(word)].keyword.value_counts())
                #df = df[df.keyword.str.contains(word)]

                # first step : transform list as string to list
                df["left_context"] = df["left_context"].apply(eval)
                df["right_context"] = df["right_context"].apply(eval)

                # on crée une colonne sentence avec la phrase initiale
                df['sentence'] = df["left_context"].str[0::2].str.join(' ') + ' ' + df['keyword'].str.replace(r"/.+$",'', regex=True) + ' ' +df["right_context"].str[0::2].str.join(' ')
                df.sentence.value_counts().head(3)

                # on crée des colonnes pour le "mot-clé" (avec forme, lemme et pos)
                import numpy as np

                df[['kw','kw_lemma','kw_pos']] = df.keyword.str.split("/", expand=True)
                #df['kw_lemma'] = df.kw_lemma.str.lower()
                df['kw_lemma'] = df.kw_lemma.str.strip()
                df['kw_pos'] = df.kw_pos.str.lower()
                df['kw_pos'] = df.kw_pos.str.strip()
                #df['kw'] = df.kw.str.lower()
                df['kw'] = df.kw.str.strip()

                # attention : si récup manuelle,  l'ordre forme lemme pos est inversé....

                df['kw_pos'],df['kw_lemma']=np.where(df['kw_pos'].str.contains(word),(df['kw_lemma'].str.lower(),df['kw_pos']),(df['kw_pos'],df['kw_lemma']))

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

                # on génére également les patrons syntaxiques :
                # - pattern_around3 = 3 mots (1 à droite gauche 1 à droite)
                # - pattern_left2 = 3 mots (2 à gauche)
                # - pattern_right2 = 3 mots (2 à droite)
                # - pattern_left3 = 4 mots (3 à gauche)
                # - pattern_right3 = 3 mots (3 à droite)

                df['pattern_around5'] = df['left_p2'] + ' ' +df['left_p1'] + ' ' + word + ' ' + df['right_p1'] + ' ' + df['right_p2']
                df['pattern_around3'] = df['left_p1'] +  ' ' + word + ' '  + df['right_p1']
                df['pattern_left2'] = df['left_p2'] + ' ' + df['left_p1']+ ' ' + word
                df['pattern_left3'] = df['left_p3'] + ' ' + df['left_p2'] + ' ' + df['left_p1']+ ' ' + word 
                df['pattern_left4'] = df['left_p4'] + ' ' +df['left_p3'] + ' ' + df['left_p2'] + ' ' + df['left_p1']+ ' ' + word 
                df['pattern_right2'] = word + ' ' +  df['right_p1'] + ' ' + df['right_p2']
                df['pattern_right3'] = word + ' ' +  df['right_p1'] + ' ' + df['right_p2'] + ' ' + df['right_p3']
                df['pattern_right4'] = word + ' ' +  df['right_p1'] + ' ' + df['right_p2'] + ' ' + df['right_p3']+ ' ' + df['right_p4']

                df['pattern_around5_lex'] = df['left_l2'] + ' ' +df['left_l1'] + ' ' + word + ' ' + df['right_l1'] + ' ' + df['right_l2']
                df['pattern_around3_lex'] = df['left_l1'] +  ' ' + word + ' '  + df['right_l1']
                df['pattern_left2_lex'] = df['left_l2'] + ' ' + df['left_l1']+ ' ' + word
                df['pattern_left3_lex'] = df['left_l3'] + ' ' + df['left_l2'] + ' ' + df['left_l1']+ ' ' + word 
                df['pattern_right2_lex'] = word + ' ' +  df['right_l1'] + ' ' + df['right_l2']
                df['pattern_right3_lex'] = word + ' ' +  df['right_l1'] + ' ' + df['right_l2'] + ' ' + df['right_l3']

                
                df.drop(columns=['left_context','right_context','left_lp1','left_lp2','left_lp3','left_lp4','left_lp5','right_lp1','right_lp2','right_lp3','right_lp4','right_lp5'], inplace=True)
                df.drop_duplicates(subset=['sentence'], inplace=True)
                df.to_csv(input_dir + lang + '.' + word + '.complete.csv', index=False)
            except Exception as e:
                var = traceback.format_exc()
                log.error('Error with ' + word + ". Error : \n" + var)
                continue

    if 'context_embeddings' in tasks:
        inputdir = './jsi_output/'
        outputdir = '../contextual_embeddings/input_files/'
        print("*"*10 + "Task : context_embeddings", ", check outputdir : " + outputdir)
        log.info("Task : context_embeddings"+ ", check outputdir : " + outputdir)
        corpus='jsi'
        lang = 'fra'
        # to save errors
        word_errors ={}
        for w in words:
            w = w.strip()
            inputfile = inputdir+lang+'.'+w+'.complete.csv'
            outputfile = outputdir + corpus+'.'+w+'.csv'
            log.info("parsing : " + w)
            if os.path.isfile(inputfile) is False:
                log.info("No input file for this word : " + w + " Relaunch retrieve_jsi_contexts_v2.py for this word")
                word_errors[w]= 'No input file'
                continue
            if os.path.isfile(outputfile):
                log.info("Already generated for word : " + w)
                continue
            try:
                df = pd.read_csv(inputfile)
                log.info(df.shape[0])
                df['year'] = df['date'].str[0:4]
                df.rename(columns={'kw':"key_word"}, inplace=True)
                df['key_word'] = df['key_word'].str.lower()
                #print(df.kw.value_counts())
                df[['year','sentence','key_word']].to_csv(outputfile, index=False)
            except Exception as e:
                var = traceback.format_exc()
                log.error('Error with this word / file ' + word + "/" + inputfile + ". Error : \n" + var)
                word_errors[w]= str(e)

        log.info("All is done. Check errors : " + str(word_errors))


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

