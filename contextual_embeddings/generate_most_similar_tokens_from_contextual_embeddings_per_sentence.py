import pandas as pd
from glob import glob
import re, pickle, os
from transformers import pipeline
from transformers.pipelines import PipelineException
import traceback
from tqdm import tqdm
import random

def load_model(lang_model):
    model  = pipeline("fill-mask", model=lang_model)#, tokenizer="camembert-base"
    return model



# main
# first jsi with camembert-base
# load model
lang_model = 'camembert-base'
print("Loading model :" + lang_model)
model = load_model(lang_model)
# load lexem input files
files = glob("input_files/*.csv")
# for each file (word+corpus) for each sentence get the fill-mask result
for file in files:
    fout = file + '.' + lang_model + '.fill_mask.pkl'
    if os.path.isfile(fout):
        print("Skipping this word as output already generated : " + fout)
        continue
    word = file.split('/')[-1].split('.')[1]
    corpus = file.split('/')[-1].split('.')[0]
    df = pd.read_csv(file)
    sentences = df[(df.key_word==word) & (df.sentence.str.len() < 505) & (df.sentence.str.contains(word))].sentence.to_list()
    #for s in sentences:
    #    if re.search(word,s) is False:
    #        sentences.remove(s)
    if len(sentences)> 2000:
        print("More than 2000 sentences for this word (" + str(len(sentences)) + "). Sampling 2000 sentences")
        sentences = random.sample(sentences, 2000)
    totals = len(sentences)
    print("Lauching fill-mask for ", len(sentences), ' sentences, word : ',word,  ', corpus : ',corpus, ', file : ', file)
    if lang_model.startswith("flaubert"):
        sentences = [re.sub(word, "<special1>", s, count=1, flags=re.I) for s in sentences]
    else:
        sentences = [re.sub(word, "<mask>",s, count=1, flags=re.I) for s in sentences]
    resTotal ={}
    #for s in sentences:
    #    try:
    #        res = model(s)
    #        for item in res:
    #            if re.search(r"\w+(-\w+){0,2}",item["token_str"]) and item["score"] > 0.1:
    #                resTotal.setdefault(item["token_str"], [] ).append((s,item["score"]))
    #    except PipelineException as e:
    #        var = traceback.format_exc()
    #        print("Error in Transformers Pipeline. Error : \n" + var)  
    #        print(word + ":"+s)                            
    #        continue
    model_generator = ((s ,model(s)) for s in sentences)
    for res in tqdm(model_generator, total= totals):
        for item in res[1]:
            if re.search(r"\w+(-\w+){0,2}",item["token_str"]) and item["score"] > 0.1:
                resTotal.setdefault(item["token_str"], [] ).append((res[0],item["score"]))
        

    print(len(resTotal), " similar tokens")
    #print(resTotal)
    pickle.dump(resTotal, open(fout, mode="wb"))
    #exit()