#!/usr/bin/env python
# coding: utf-8

# # Ce programme effectuer l'analyse morphosyntaxique des données d'Europaena News (stockées dans Apache Solr et récupérées pour chaque lexème candidat)
# 

import pandas as pd
# fonctions pour appeler udpipe et parser le résultat
import requests, time, re, os
from glob import glob

def get_udpipe_models():
    resp = requests.get('http://lindat.mff.cuni.cz/services/udpipe/api/models')
    print(resp.json())

# to be done : handle list of sentences    
def udpipe_analysis_bk(data, model='french-ud-2.0-170801',tokenizer=True, tagger=True, parser=False, output='conllu'):
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

def udpipe_analysis(data, model='french-ud-2.0-170801',tokenizer=True, tagger=True, parser=False, output='conllu'):
    ''' Retrieve udpipe analysis and return it (connllu)'''
    if type(data) is list:
        #data = data[0]
        data = "\n\n".join(data)
    params={'data': data, 'model':model,'input':'horizontal','output':output, 'tokenizer':True, 'tagger':True, 'parser':True}
    #time.sleep(1)
    try:
        resp =  requests.post('https://lindat.mff.cuni.cz/services/udpipe/api/process', params=params)
        return resp.json()
    except Exception as e:
        print("Error with this request :" + data + ". Error : " + str(e))
        return ""


def udpipe_analysis_file(filename, model='french-ud-2.0-170801',tokenizer=True, tagger=True, parser=False, output='conllu'):
    ''' Retrieve udpipe analysis and return it (connllu)'''
    data_file = open(filename, "rb")
    params={'model':model,'input':'horizontal','output':output, 'tokenizer':True, 'tagger':True, 'parser':True}
    data = {'data':data_file}
    #time.sleep(1)
    try:
        resp =  requests.post('https://lindat.mff.cuni.cz/services/udpipe/api/process', params=params,files=data)
        return resp.json()
    except Exception as e:
        print("Error with this request :" + filename + ". Error : " + str(e))
        return ""

def load_sentences(filename, token=False, limit=False):
    df = pd.read_csv(filename)
    df['sentence'] = df['sentence'].str.replace('’',"'")
    if token:
        s = df[df.key_word==token]["sentence"]
        if limit:
            if s.shape[0]> limit:
                s = s.sample(n=limit, random_state=1).tolist()
            else:
                return s
        else:
            return s
    else:
        s = df["sentence"].tolist()
        if limit:
            if s.shape[0]> limit:
                s = s.sample(n=limit, random_state=1).tolist()
            else:
                return s
        else:
            return s
    return s


if __name__ == '__main__':
    print("udpipe analysis")
    inputfiles = "./input_files/gallica.*.csv"
    files = glob(inputfiles)
    nb = len(files)
    #print(nb, " file to parse")
    for filename in sorted(files):
        print(nb, " left files to parse")
        nb = nb -1
        fileout = filename+'.udpipe.conllu'
        if os.path.isfile(fileout):
            print("already parsed : " +  filename)
            continue
        token = filename.split('/')[-1].split('.')[1]
        s = load_sentences(filename,token,3000)
        print(len(s), " sentences for file : ", filename)
        with open('sentences.tmp', mode="w") as fout:
            fout.write("\n\n".join(s))
        #exit()
        resp = udpipe_analysis_file("sentences.tmp",tokenizer=True, tagger=True, parser=True)
        #print(resp)
        with open(fileout, mode="w") as fout:
            fout.write(resp["result"])

	#udpipe_analysis("l'orage a éclaté en milieu d'après-midi.",tokenizer=True, tagger=True, parser=True)
