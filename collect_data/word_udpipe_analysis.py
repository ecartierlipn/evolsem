#!/usr/bin/env python
# coding: utf-8

# # Ce programme effectuer l'analyse morphosyntaxique des données d'Europaena News (stockées dans Apache Solr et récupérées pour chaque lexème candidat)
# 
# Les fichiers se trouvent dans le sous-répertoire `./solr_results/`. Ils ont été récupérés par le programme `./words_contexts_local_json_from_solr_query_europanea_news.py`.


# ## traitement des textes
# 
# - analyse morphosyntaxique des phrases (udpipe)
# - découpage du résultat en séquences 5 mots à droite et à gauche pour exploration détaillée des distributions et des évolutions de distribution

# In[1]:

import pandas as pd
# fonctions pour appeler udpipe et parser le résultat
import requests, time, re

def get_udpipe_models():
    resp = requests.get('http://lindat.mff.cuni.cz/services/udpipe/api/models')
    print(resp.json())

# to be done : handle list of sentences    
def udpipe_analysis(data, model='french-ud-2.0-170801',tokenizer=True, tagger=True, parser=False, output='conllu'):
    ''' Retrieve udpipe analysis and return it (connllu)'''
    if type(data) is list:
        #data = data[0]
        data = "\n\n".join(data)
    #print(data)
    clean = re.sub('<b><mark>','',data, re.I)
    clean2 = re.sub('</mark></b>','',clean, re.I)
    
    params={'data': clean2, 'model':model,'input':'horizontal','output':output, 'tokenizer':True, 'tagger':True, 'parser':True}
    #time.sleep(1)
    try:
        resp =  requests.post('https://lindat.mff.cuni.cz/services/udpipe/api/process', params=params)
        ana = resp.json()['result']
        #print(resp)
        pos_text = [elt for elt in ana.split("\n")  if re.search(r"^[0-9]+",elt)]
        res=[]
        for elt in pos_text:
            infos = elt.split("\t")
            ch = infos[1] + '/' + infos[2] + '/' +infos[3] + '/' + infos[5]
            res.append(ch)
        #print(res)
        return " ".join(res)
    except Exception as e:
        print("Error with this request :" + data + ". Error : " + str(e))
        return ""



if __name__ == '__main__':
	print("testing udpipe")
	udpipe_analysis("l'orage a éclaté en milieu d'après-midi.")

#df['pos-text'] = df.sentence.apply(lambda x : udpipe_analysis(x))
#df.to_csv(outputdir + newspaper + '.sentences.conllu.csv')
#df.info()


# now for all words!
#import os
#from glob import glob
#import pandas as pd

#input_dir = './solr_results/'
#output_dir = './solr_results/'
#lang='fr'

#words = ['arriver','bouillon','butiner','bureau','cabinet','caboche','chômage','col','confiner','courrier','crudité','daim','dauber','desserte','déménager','enguirlander','fléau','foirer','frein','froc','fumer','gratin','glacière','glaner','griser','lampiste','marronnier','meurtrir','mortier','mouture','mâchoire','profil','sabrer','soûler','toiser','trapper','écurie','épanchement','éreinter','étrenner']
#for word in words:
#    if os.path.isfile(input_dir + word + '.sentences.conllu.csv'):
#        print(word + " already retrieved. Skipping.")
#        continue
#    df = pd.read_json(input_dir + word + '1910-1920.200.json.spellcheck.json', orient="records")
#    df['count'] = 1
#    df['datetime'] = pd.to_datetime(df['date'], infer_datetime_format=True)
#    df['year'] = df['datetime'].dt.strftime('%Y')
#    df['10years'] = df['datetime'].apply(lambda x: (x.year//10)*10)#dt.to_period("10Y")
#    print(word, df.info())
#    df.rename({'hl':'sentence'}, axis=1, inplace=True)
#    df['pos-text'] = df.sentence.apply(lambda x : udpipe_analysis(x))
#    df[['date','source','id','sentence','pos-text']].to_csv(output_dir + word + '.sentences.conllu.csv', index=False)
    #df2 = df.set_index('datetime')
                    

#exit()
# ### Découpage de l'analyse pos-text en composantes (5 mots à gauche, 5 mots à droite) avec atomisation des infos (word, lemme, pos, subpos)

# In[52]:


input_dir = './solr_results/'
output_dir = './solr_results/'
lang='fr'
word='autoriser'

def split_pos_text(x,word=word):
    #print(x['pos-text'])
    data = re.split("\s+", str(x['pos-text']))
    #print(data)
    for i, value in enumerate(data):
        if re.search(r"^"+word+ "/",value, re.I):
            kw= data[i]
            left_context = data[i-5:i]
            right_context = data[i+1:i+6]
            return pd.Series([kw,left_context, right_context], index=['keyword', 'left_context', 'right_context'])

        
# now for all words!

input_dir = './solr_results/'
output_dir = './solr_results/'
lang='fr'

    
files = glob(input_dir + '*.sentences.conllu.csv')
words = [re.sub(input_dir + r"(.+?)\.sentences\.conllu\.csv", r"\1", f) for f in files]
print(words)
words= ['profil']

for word in words:
    if os.path.isfile(input_dir + word + '.sentences.conllu.all.csv'):
        print("Already retrieved. Skipping.")
        continue

    df = pd.read_csv(output_dir + word + '.sentences.conllu.csv')
    print(df.info())
    df[['keyword','left_context','right_context']] = df.apply(split_pos_text,word=word, axis=1) # , result_type="expand"

    ########### keyword
    df[['kw','kw_lemma','kw_pos','kw_subpos']] = df.keyword.str.split("/", n=3, expand=True)
    ############ left word/lemma/pos/subpos
    df['left1'] = df['left_context'].str[-1].str.strip()
    df['left2'] = df['left_context'].str[-2].str.strip()
    df['left3'] = df['left_context'].str[-3].str.strip()
    df['left4'] = df['left_context'].str[-4].str.strip()
    df['left5'] = df['left_context'].str[-5].str.strip()

    ############ right word/lemma/pos/subpos
    df['right1'] = df['right_context'].str[0].str.strip()
    df['right2'] = df['right_context'].str[1].str.strip()
    df['right3'] = df['right_context'].str[2].str.strip()
    df['right4'] = df['right_context'].str[3].str.strip()
    df['right5'] = df['right_context'].str[4].str.strip()

    # subinfo left
    df[['left_w1','left_l1','left_p1','left_subp1']] = df.left1.str.split("/", n=3, expand=True)
    df[['left_w2','left_l2','left_p2','left_subp2']] = df.left2.str.split("/", n=3, expand=True)
    df[['left_w3','left_l3','left_p3','left_subp3']] = df.left3.str.split("/", n=3, expand=True)
    df[['left_w4','left_l4','left_p4','left_subp4']] = df.left4.str.split("/", n=3, expand=True)
    df[['left_w5','left_l5','left_p5','left_subp5']] = df.left5.str.split("/", n=3, expand=True)

    # subinfo right
    df[['right_w1','right_l1','right_p1','right_subp1']] = df.right1.str.split("/", n=3, expand=True)
    df[['right_w2','right_l2','right_p2','right_subp2']] = df.right2.str.split("/", n=3, expand=True)
    df[['right_w3','right_l3','right_p3','right_subp3']] = df.right3.str.split("/", n=3, expand=True)
    df[['right_w4','right_l4','right_p4','right_subp4']] = df.right4.str.split("/", n=3, expand=True)
    df[['right_w5','right_l5','right_p5','right_subp5']] = df.right5.str.split("/", n=3, expand=True)

    # syntaxic patterns
    # on génére également les patrons syntaxiques :
    # - pattern_around5 = 5 mots (2 à droite gauche 2 à droite)
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

    ########### et les patrons lexicaux correspondants

    df['pattern_around5_lex'] = df['left_l2'] + ' ' +df['left_l1'] + ' ' + word + ' ' + df['right_l1'] + ' ' + df['right_l2']
    df['pattern_around3_lex'] = df['left_l1'] +  ' ' + word + ' '  + df['right_l1']
    df['pattern_left2_lex'] = df['left_l2'] + ' ' + df['left_l1']+ ' ' + word
    df['pattern_left3_lex'] = df['left_l3'] + ' ' + df['left_l2'] + ' ' + df['left_l1']+ ' ' + word 
    df['pattern_left4_lex'] = df['left_l4'] + ' ' +df['left_l3'] + ' ' + df['left_l2'] + ' ' + df['left_l1']+ ' ' + word 
    df['pattern_right2_lex'] = word + ' ' +  df['right_l1'] + ' ' + df['right_l2']
    df['pattern_right3_lex'] = word + ' ' +  df['right_l1'] + ' ' + df['right_l2'] + ' ' + df['right_l3']
    df['pattern_right4_lex'] = word + ' ' +  df['right_l1'] + ' ' + df['right_l2'] + ' ' + df['right_l3']+ ' ' + df['right_l4']


    #df.right_p1.value_counts()
    df.to_csv(output_dir + word + '.sentences.conllu.all.csv', index=False)


