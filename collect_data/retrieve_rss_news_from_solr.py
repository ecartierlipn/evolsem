# solr functions
import pysolr, json, requests
import os,re, sys
import glob
import pandas as pd
import traceback
import logging
import logging.config
import pickle
from datetime import datetime
# mysql
import mysql.connector
from mysql.connector import Error


# mysql connection parameters
host = 'localhost'
user = 'root'
password = 'neoveille'
db = 'evolsem'

# mysql                    
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



# mysql
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


# SOLR functions
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
        print("Error Apache Solr  search query :" + str(e))
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

def query_solr_all_results_nohl(solr,query, params):
    totalres = []
    # first check number of results (<50 == discard)
    done = False
    while done is False:
        results = query_solr(solr, query, params)
        #print(params['cursorMark'], ' / ', results.hits)
        #exit()
        for doc in results.docs:
            totalres.append(doc)
        if params['cursorMark'] == results.nextCursorMark:
            done = True
        params['cursorMark'] = results.nextCursorMark
    return totalres

def sentence_tokenizer(sent, word):
    sentences = re.compile(r"[\.!\?\\n]+ ").split(sent)
    #print(sentences)
    for s in sentences:
        if re.search(r"\b" + word + r".?\b", s, re.I):
            return s
    return False

################################## main
def main():
    # Apache Solr parameters
    solr_host = 'https://tal.lipn.univ-paris13.fr/solr/'
    solr_collection = 'rss_french'
    solr =  pysolr.Solr(solr_host+ solr_collection, always_commit=True)
    try : 
        solr.ping()
    except Exception as e:
        print("Problem with Apache Solr Server. Check error message : " + str(e))
        exit()


    # define task(s) and words
    tasks = ['word_synthesis','word_contexts','clean_word_contexts','contexts_embeddings','word_contexts_mysql','all']
    task = 'word_contexts_mysql'
    ######## reading wordlist
    words = {}
    from_wordlist = 'file_csv' # 'file', 'pickle','word'
    word_filter = [15] # ie noun, 15 for verb

############### retrieve wordlists
# read candidat lists for verbs and nouns
    if from_wordlist =='word':
        words = {'réaliser':15}
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
        with open('liste-mots.csv') as fin:
            for line in fin:
                a =  re.search(r"^\w+(-\w+)?$", line.strip())
                if a:
                    words[line.strip()]="X"
                    #log.info(a.group(1))
        log.info(str(words) +  str(len(words)) +  " elements")
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


    log.info("*"*20 + "\nLauching processs with following paramaters\nTasks : " + str(task) + "\nWordlist : " +  str(words) +  "\n" + "*"*20)
    print("*"*20 + "\nLauching processs with following paramaters\nTasks : " + str(task) + "\nWordlist : " +  str(words) +  "\n" + "*"*20)

    outputdir = './solr_rssfeeds_output/'
    os.makedirs(outputdir, exist_ok=True)
    if task in ['all','word_synthesis']:
        print("*"*10 + "Task : word_sythesis", ", check outputdir : " + outputdir)
        log.info("Task : word_sythesis"+ ", check outputdir : " + outputdir)
        if os.path.isfile(solr_collection + '.word_counts.csv') is False:
            # open in write mode
            fout =  open(solr_collection + '.word_counts.csv', mode="w")
            fout.write("word,period,count\n")
            for word in words:
                    params = {'rows':1}
                    query = 'contents:'+word
                    res = query_solr(solr, query, params)
                    if res:
                        #print(res.hits)
                        fout.write(word + ',2014-2020,' + str(res.hits) + "\n")
            fout.close()
        else:
            print("*"*10 + "Task : word_sythesis already done", ", check file : " + solr_collection + '.word_counts.csv')
            log.info("*"*10 + "Task : word_sythesis already done", ", check file : " + solr_collection + '.word_counts.csv')

        # now retrieve word freq to get data (if overall freq > 50000 we will sample by year)
        df = pd.read_csv(solr_collection + '.word_counts.csv')
        print(df.info())
        print(df[(df['count'] < 500000)]['count'].sum())
        words = df[(df['count'] < 500000)].word.value_counts().index.to_list()
        wordfreq = df.word.value_counts().to_dict()
        print(len(words), " words")
        print(wordfreq)

        if len(words)==0:
            print("No word to retrieve. Check if words frequency is lesser than 500000. Or change paramters above line 136")
            exit()
    if task in ['all','word_contexts']:
        print("*"*10 + "Task : word_contexts", ", check outputdir : " + outputdir)
        log.info("Task : word_contexts"+ ", check outputdir : " + outputdir)
        word_errors={}
        error_file = './log/retrieve_rss_news_from_solr.word_errors.json'
        for word in words:
            word = word.strip()
            if os.path.isfile(outputdir + word+'.json'):
                print("already retrieved. Skipping. (" + outputdir + word +'.json')
                log.info("already retrieved. Skipping. (" + outputdir + word +'.json')
                continue
                
            params = {
                    'sort':'link asc',
                    'rows':50,
                    'cursorMark':'*',
                    'fl':'source,dateS,link,contents'
            }
            print("retrieving data for : " + word)        
            query = 'contents:"'+word+'"'
            try:
                docs = query_solr_all_results_nohl(solr,query, params)
                res=[]
                if docs:
                    for doc in docs:
                        tmpres=[]
                        parag = re.split("\n", doc['contents'][0])
                        #print(parag)
                        for p in parag:
                            #print(doc)
                            if re.search(r"\b" + word + r"\b",p, re.I):
                                tmpres.append(p)
                        if len(tmpres)>0:
                            del(doc['contents'])
                            doc['contents']=list(set(tmpres))
                            res.append(doc)
                        else:
                            print("No match for this doc : ", doc['contents'])                        
                    json.dump(res, open(outputdir + word+'.json', mode='w'), indent=4)
                    print("Data stored in " + outputdir + word+'.json')
                else:
                    print("Error with this word")
            except Exception as e:
                print("error with this word : " + word + '. Error : ' + str(e))
                word_errors[word]=str(e)
                continue

        if len(word_errors)>0:
            print("All is done but some errors occurred. Check error file : " + error_file)
            json.dump(word_errors,open(error_file, mode="w"))
        else:
            print("All is done. No errors")
            if os.path.isfile(error_file):
                os.remove(error_file)
    if task in ['all','clean_word_contexts']:
        print("*"*10 + "Task : clean_word_contexts", ", check outputdir : " + outputdir)
        log.info("Task : clean_word_contexts"+ ", check outputdir : " + outputdir)
        for word in words:
            word = word.strip()
            log.info("parsing word : " + word) 
            if os.path.isfile(outputdir + word + '.csv'):
                log.info("already parsed. Skipping. (" + outputdir + word +'.csv')
                print("already parsed. Skipping. (" + outputdir + word +'.csv')
                continue
            try:
                with open(outputdir + word + '.json','r') as f:
                    data = json.loads(f.read())
                # Flatten data
                df = pd.json_normalize(data, record_path =['contents'],meta=['dateS', 'link','source'], errors="ignore").rename(columns={0: "sentence"})      #, record_path =['contents']          
                #print(df.info)
                #print(df.head())
                #exit()
                #df = pd.read_json(outputdir + word + '.json', orient="records")
            except Exception as e:
                var = traceback.format_exc()
                log.error('Error with ' + word + ". Error : \n" + var)
                print('Error with ' + word + ". Error : \n" + var)
                continue
#            except:
#                log.info("No file found for [" + word + ", "+ outputdir + word + ".json]. Skipping.")
#                continue
            try:
                df.dropna(inplace=True)
                # on ajoute les données temporelles (pour l'année)
                df['datetime'] = pd.to_datetime(df['dateS'], infer_datetime_format=True)
                df['year'] = df['datetime'].dt.strftime('%Y')
                df['sentence']= df.sentence.str.replace(r"\s+", " ", regex=True)
                df['sentence']= df.sentence.apply(sentence_tokenizer, word=word)
                df.drop_duplicates(inplace=True)
                df.to_csv(outputdir + word + '.csv', index=False)
                log.info("dataframe saved to : [" + outputdir + word + '.csv], ' + str(df.shape[0]) + " entries")
                print("dataframe saved to : [" + outputdir + word + '.csv], ' + str(df.shape[0]) + " entries")
            except Exception as e:
                var = traceback.format_exc()
                log.error('Error with ' + word + ". Error : \n" + var)
                print('Error with ' + word + ". Error : \n" + var)
                continue

    if task in ['all','context_embeddings']:
        inputdir = outputdir
        outputdir = '../visualization/input_files/'
        print("*"*10 + "Task : context_embeddings", ", check outputdir : " + outputdir)
        log.info("Task : context_embeddings"+ ", check outputdir : " + outputdir)
        corpus='jsi'
        lang = 'fra'
        # to save errors
        word_errors ={}
        for w in words:
            w = w.strip()
            inputfile = inputdir + w + '.csv'
            outputfile = outputdir + corpus+'.'+w+'.csv'
            log.info("parsing : " + w)
            if os.path.isfile(inputfile) is False:
                log.info("No input file for this word : " + w + " Check previous tasks for this word")
                word_errors[w]= 'No input file'
                continue
            if os.path.isfile(outputfile):
                log.info("Already generated for word : " + w)
                continue
            try:
                df = pd.read_csv(inputfile)
                log.info(df.shape[0])
                #df['year'] = df['date'].str[0:4]
                #df.rename(columns={'kw':"key_word"}, inplace=True)
                df['key_word'] = w
                #print(df.kw.value_counts())
                df[['year','sentence','key_word','source','link']].to_csv(outputfile, index=False)
            except Exception as e:
                var = traceback.format_exc()
                log.error('Error with this word / file ' + word + "/" + inputfile + ". Error : \n" + var)
                word_errors[w]= str(e)

        log.info("All is done. Check errors : " + str(word_errors))
    #exit()
    # JSI Corpus sentences
    if task in ['all','word_contexts_mysql']:
        error_file = './log/retrieve_rss_news_from_solr.py.errors.json'
        ## try to open the words not saved during the last run
        if os.path.isfile(error_file):
            words = json.load(open(error_file))
            print("Saving from last run errors : " + str(len(words.keys())) + " words")
        error_words={}
        input_dir = outputdir

        files = glob.glob(input_dir+"*.csv")
        files = [f for f in files if  datetime.utcfromtimestamp(os.path.getctime(f)).date() > datetime.strptime('2022-02-02', '%Y-%m-%d').date() ]
        #for f in files:
        #    print(f, datetime.utcfromtimestamp(os.path.getctime(f)).date())
        #print(files)
        #exit()
        words = [f.split('/')[-1].split('.')[0] for f in files]
        print(words, len(words))

        for w in words:
            try:
                print("parsing : " + w)
                df = pd.read_csv(input_dir + w + '.csv') # corpus+
                print("Initial shape : ", df.shape)
                df.dropna(inplace=True)
                df = df[df.sentence != 'False']
                #df = df[df.key_word.str.contains(r"^"+w+r".?$", regex=True)]
                #print("Shape after filtering word form : ", df.shape)
                freq1 = df.shape[0]
                #print(df.info(verbose=True))
                #exit() 
                #print("word forms : ", df.key_word.value_counts())
                #print(df['sentence'].head())
                #exit()
                update_lexies_corpus_freq_to_mysql("wiktionary_lexicon", w, str(freq1), "jsi")
                print("storing contexts in db")
                df['datetime'] = pd.to_datetime(df['datetime'], infer_datetime_format=True) # 2018-04-20T14:54:38Z
                df['date'] = df['datetime'].dt.strftime('%Y-%m-%d').astype(str)
                if df.shape[0]>10000:
                    df = df.sample(n=10000, random_state=5)
                print(df.info())
                df.rename(columns={'link':'url','source':'journal'}, inplace=True)
                df['corpus']='rss_french'
                df['key_word']=w
                df['word']=w
                df['pos']=''
                df['sentence'] = df.apply(lambda x : x['sentence'].replace(x['key_word'],"<mark><b>" + x['key_word'] + "</b></mark>"),1)    
                #df['sentence'] = df['sentence'].str.replace(df['key_word'].str.value, "<mark><b>" + df['key_word'].str.value + "</b></mark>")
                res, detail = save_sentences_to_mysql('sentences2', df[['word','pos','key_word','corpus','journal','url','date','sentence']].to_dict(orient='records'), debug=True)
                if res == False:
                    print("error in save_sentences_to_mysql('sentences2', df.to_dict(orient='records')) function.", detail)
                    exit()

            except Exception as e:
                var = traceback.format_exc()
                print("Error in : 'word_contexts_mysql' task. Error : \n" + var)                            
                error_words[w]=var                           
        if len(error_words)> 0:
            print('All is done except for following words.Please check : ' + error_file )
            json.dump(error_words, open(error_file, mode='w'))
        else:
            print("All is done. No errors.")
            if os.path.isfile(error_file):
                os.remove(error_file)


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
