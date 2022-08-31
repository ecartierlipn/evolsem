
# https://mccormickml.com/2019/05/14/BERT-word-embeddings-tutorial/#33-creating-word-and-sentence-vectors-from-hidden-states

import re, pickle,os,sys
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import torch
from transformers import CamembertModel, CamembertTokenizer
from transformers import pipeline
import multiprocessing as mp
# OPTIONAL: if you want to have more information on what's happening, activate the logger as follows
#import logging
#logging.basicConfig(level=logging.INFO)


def load_model(model='camembert-base', eval=True):
   # Load pre-trained model tokenizer (vocabulary)
   tokenizer = CamembertTokenizer.from_pretrained(model)
   # Load pre-trained model (weights) Camembert
   model = CamembertModel.from_pretrained(model,
                                    output_hidden_states=True # Whether the model returns all hidden-states.
                                    )
   # Put the model in "evaluation" mode, meaning feed-forward operation.
   if eval:
      model.eval()
   return tokenizer, model

def load_pos_tagger(model_name="gilf/french-camembert-postag-model",eval=True):
    # you can also try : gilf/french-postag-model
    from transformers import AutoTokenizer, AutoModelForTokenClassification
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForTokenClassification.from_pretrained(model_name)
    if eval:
        model.eval()
    return tokenizer, model     

def text_pos_tagging(sentence, tokenizer, model):
    nlp_token_class = pipeline('ner', model=model, tokenizer=tokenizer, aggregation_strategy='simple')
    return nlp_token_class(sentence)    

def get_embeddings(word, sentence, model, tokenizer, debug=True):
    # Split the sentence into tokens (camembert)
    tokenized_text = tokenizer.tokenize(sentence)
    if debug==True:
        print(tokenized_text)
    # word tokenization (to retrieve pos)
    tokenized_word = tokenizer.tokenize(word)
    if debug==True:
        print(tokenized_word)
    # get pos of word: if composed of several tokens, you need to sum the vectors, otherwise, you get the vector for pos
    try:
        if len(tokenized_word)==1:
            pos = tokenized_text.index(tokenized_word[0])
        else:
            pos = tokenized_text.index(tokenized_word[1])
        if debug==True:
            print("tokenization text: ", tokenized_text, "tokenized word : ",tokenized_word,"intial position : ", pos,"end of position (exclusive) : ", pos + len(tokenized_word))
    except Exception as e:
        print("No occurrence of " + word + ' (tokenized: ' + str(tokenized_word) + ', tokenized sentence :' + str(tokenized_text))
        return (False, -1)
    # Map the token strings to their vocabulary indeces.
    indexed_tokens = tokenizer.convert_tokens_to_ids(tokenized_text)
    # Convert inputs to PyTorch tensors
    tokens_tensor = torch.tensor([indexed_tokens])
    # get embeddings hidden states
    with torch.no_grad():
        outputs = model(tokens_tensor)
        hidden_states = outputs[2]
    
    # hidden_states - current dimensions:
    #`[# layers, # batches (sentences), # tokens, # features]`
    #Desired dimensions:
    #`[# tokens, # layers, # features]`    
    # Concatenate the tensors for all layers. We use `stack` here to
    # create a new dimension in the tensor.
    token_embeddings = torch.stack(hidden_states, dim=0)
    if debug==True:
        print("Initial embeddings : ", token_embeddings.size())
    # Remove dimension 1, the "batches (sentences).
    token_embeddings = torch.squeeze(token_embeddings, dim=1)
    if debug==True:
        print("After batches removal : ",token_embeddings.size())
    # Swap dimensions 0 (layers) and 1 (tokens pos)=> [tokens, layers, tensors]
    token_embeddings = token_embeddings.permute(1,0,2)
    if debug == True:
        print("Final Embeddings : ", token_embeddings.size())
    
    # get embeddings of word = sum of 4 four last layers (to be parameterized)
    token_vecs_sum = []
    for token in token_embeddings[pos:pos + len(tokenized_word)]:
        sum_vec = torch.sum(token[-4:], dim=0)
        token_vecs_sum.append(sum_vec)
    return (torch.stack(token_vecs_sum, dim=0).sum(dim=0),pos)

def get_embeddings_iterator(word, sentence, model, tokenizer, debug=True):
    # Split the sentence into tokens (camembert)
    # first ensure the focused word is separated from other elements (especially ')
    sentence = re.sub(r"\b("+word.lower()+r")\b", r" \1 ", sentence.lower())
    tokenized_text = tokenizer.tokenize(sentence)
    if debug==True:
        print(tokenized_text)
    # word tokenization (to retrieve pos)
    tokenized_word = tokenizer.tokenize(word)
    if debug==True:
        print(tokenized_word)
    # get pos of word: if composed of several tokens, you need to sum the vectors, otherwise, you get the vector for pos
    try:
        if len(tokenized_word)==1:
            pos = tokenized_text.index(tokenized_word[0])
        else:
            pos = tokenized_text.index(tokenized_word[1])
        if debug==True:
            print("tokenization text: ", tokenized_text, "tokenized word : ",tokenized_word,"intial position : ", pos,"end of position (exclusive) : ", pos + len(tokenized_word))
    except Exception as e:
        print("No occurrence of " + word + ' (tokenized: ' + str(tokenized_word) + ', tokenized sentence :' + str(tokenized_text))
        return (False, -1)
    # Map the token strings to their vocabulary indeces.
    indexed_tokens = tokenizer.convert_tokens_to_ids(tokenized_text)
    # Convert inputs to PyTorch tensors
    tokens_tensor = torch.tensor([indexed_tokens])
    # get embeddings hidden states
    with torch.no_grad():
        outputs = model(tokens_tensor)
        hidden_states = outputs[2]
    
    # hidden_states - current dimensions:
    #`[# layers, # batches (sentences), # tokens, # features]`
    #Desired dimensions:
    #`[# tokens, # layers, # features]`    
    # Concatenate the tensors for all layers. We use `stack` here to
    # create a new dimension in the tensor.
    token_embeddings = torch.stack(hidden_states, dim=0)
    if debug==True:
        print("Initial embeddings : ", token_embeddings.size())
    # Remove dimension 1, the "batches (sentences).
    token_embeddings = torch.squeeze(token_embeddings, dim=1)
    if debug==True:
        print("After batches removal : ",token_embeddings.size())
    # Swap dimensions 0 (layers) and 1 (tokens pos)=> [tokens, layers, tensors]
    token_embeddings = token_embeddings.permute(1,0,2)
    if debug == True:
        print("Final Embeddings : ", token_embeddings.size())
    
    # get embeddings of word = sum of 4 four last layers (to be parameterized)
    token_vecs_sum = []
    for token in token_embeddings[pos:pos + len(tokenized_word)]:
        sum_vec = torch.sum(token[-4:], dim=0)
        token_vecs_sum.append(sum_vec)
    return (torch.stack(token_vecs_sum, dim=0).sum(dim=0),pos)

# EC: does not work on empêcher, no time to checl why
def get_embeddings_parallel(i, word, sentence, year, model, tokenizer, debug=False):
    print(i)
    # Split the sentence into tokens (camembert)
    tokenized_text = tokenizer.tokenize(sentence)
    if debug==True:
        print(tokenized_text)
    # word tokenization (to retrieve pos)
    tokenized_word = tokenizer.tokenize(word)
    if debug==True:
        print(tokenized_word)
    # get pos of word: if composed of several tokens, you need to sum the vectors, otherwise, you get the vector for pos
    try:
        if len(tokenized_word)==1:
            pos = tokenized_text.index(tokenized_word[0])
        else:
            pos = tokenized_text.index(tokenized_word[1])
        if debug==True:
            print("tokenization text: ", tokenized_text, "tokenized word : ",tokenized_word,"intial position : ", pos,"end of position (exclusive) : ", pos + len(tokenized_word))
    except Exception as e:
        print("No occurrence of " + word + ' (tokenized: ' + str(tokenized_word) + ', tokenized sentence :' + str(tokenized_text))
        return i, False, 1,0,0,0
    # Map the token strings to their vocabulary indeces.
    indexed_tokens = tokenizer.convert_tokens_to_ids(tokenized_text)
    # Convert inputs to PyTorch tensors
    tokens_tensor = torch.tensor([indexed_tokens])
    # get embeddings hidden states
    with torch.no_grad():
        outputs = model(tokens_tensor)
        hidden_states = outputs[2]
    
    # hidden_states - current dimensions:
    #`[# layers, # batches (sentences), # tokens, # features]`
    #Desired dimensions:
    #`[# tokens, # layers, # features]`    
    # Concatenate the tensors for all layers. We use `stack` here to
    # create a new dimension in the tensor.
    token_embeddings = torch.stack(hidden_states, dim=0)
    if debug==True:
        print("Initial embeddings : ", token_embeddings.size())
    # Remove dimension 1, the "batches (sentences).
    token_embeddings = torch.squeeze(token_embeddings, dim=1)
    if debug==True:
        print("After batches removal : ",token_embeddings.size())
    # Swap dimensions 0 (layers) and 1 (tokens pos)=> [tokens, layers, tensors]
    token_embeddings = token_embeddings.permute(1,0,2)
    if debug == True:
        print("Final Embeddings : ", token_embeddings.size())
    
    # get embeddings of word = sum of 4 four last layers (to be parameterized)
    token_vecs_sum = []
    for token in token_embeddings[pos:pos + len(tokenized_word)]:
        sum_vec = torch.sum(token[-4:], dim=0)
        token_vecs_sum.append(sum_vec)

    return i, torch.stack(token_vecs_sum, dim=0).sum(dim=0),token, sentence, pos, year

def explore_layers(word, sentence, model, tokenizer, debug=True):
   # Split the sentence into tokens (camembert)
   tokenized_text = tokenizer.tokenize(sentence)
   if debug==True:
      print(tokenized_text)
   # word tokenization (to retrieve pos)
   tokenized_word = tokenizer.tokenize(word)
   if debug==True:
      print(tokenized_word)
   # get pos of word: if composed of several tokens, you need to sum the vectors, otherwise, you get the vector for pos
   try:
      if len(tokenized_word)==1:
         pos = tokenized_text.index(tokenized_word[0])
      else:
         pos = tokenized_text.index(tokenized_word[1])
      if debug==True:
         print("tokenization text: ", tokenized_text, "tokenized word : ",tokenized_word,"intial position : ", pos,"end of position (exclusive) : ", pos + len(tokenized_word))
   except Exception as e:
      print("No occurrence of " + word + ' (tokenized: ' + str(tokenized_word) + ', tokenized sentence :' + str(tokenized_text))
      return (False, -1)
   # Map the token strings to their vocabulary indeces.
   indexed_tokens = tokenizer.convert_tokens_to_ids(tokenized_text)
   # Convert inputs to PyTorch tensors
   tokens_tensor = torch.tensor([indexed_tokens])
   # get embeddings hidden states
   with torch.no_grad():
      outputs = model(tokens_tensor)
      hidden_states = outputs[2]
   # now explore
   # For the token in our sentence, select its feature values from  all layers
   token_i = pos
   fig, axs = plt.subplots(4, 3)
   i=0
   j=0
   for layer in range(1,13):
      print(i,j)
      vec = hidden_states[layer][0][token_i]
      # Plot the values as a histogram to show their distribution.
      axs[i,j].hist(vec.numpy(), bins=200)
      axs[i,j].set_title("layer " + str(layer))
      if j==2:
         i=i+1
         j=0
      else:
         j=j+1
   plt.tight_layout()
   plt.show()
    
###################################  main



# get embeddings
#w = 'dormir'
#s = 'il faut dormir la nuit'
#res,pos = get_embeddings(w,s,model,tokenizer, debug=True)
#print(res[0:10],pos)
#exit()

# explore_layers
#w = 'dormir'
#s = 'il faut dormir la nuit'
#res,pos = explore_layers(w,s,model,tokenizer, debug=True)
#print(res[0:10],pos)

def main_one_process():
   tokenizer, model = load_model()

   inputdir='input_files/'
   outputdir = 'token_embeddings/'

   # read candidate lists for verbs and nouns
   verbes = {}
   with open('../collect_data/liste_candidats_verbes_vieilli.txt') as fin:
      for line in fin:
         a =  re.search(r"^([^_]+)_[0-9]", line)
         if a:
               verbes[re.sub(r"\s*\*",'',a.group(1).strip())]="V"
               #print(a.group(1))
   vlist = sorted(verbes, reverse=True)

   corpora = ['gallica','jsi']
   vlist=['empêcher']
   # load sentences per year for each word in wordlist
   for w in vlist:
      w = w.strip()
      if os.path.isfile(outputdir+w+'.pkl'):
         print("already done :" + w)
         continue
      usages = []
      for corp in corpora:
         inputfile = inputdir+corp+'.'+w+'.csv'
         if os.path.isfile(inputfile) is False:
               print("No data for this word : " + w + ', ' + inputfile)
               continue
         print("Parsing : ", w, inputfile )
         df = pd.read_csv(inputfile)
         print(df.shape[0])
         df = df[df.key_word==w]
         data = df.to_records(index=False).tolist()
         print("Number of sentences with exact form : " + str(len(data)))
         for i, elt in enumerate(data):
               if len(elt) == 3 and len(str(elt[0]))==4 and len(elt[1])>0 and len(elt[2])>0:
                   sentence = re.sub(r"\b("+w+r")\b", r" \1 ", elt[1].lower())
                   (vector, pos) = get_embeddings(elt[2].lower(),sentence,model,tokenizer, debug=False)
                   if vector is False:
                       print("Failure for sentence : " + elt[1] + ', token : ' + elt[2])
                       continue
                   #print(i)
                   usages.append((vector,elt[2],elt[1],pos,elt[0])) # (vector, token, sentence, position, year)
      # save tmp usages to already saved or create new pickle
      if len(usages)>0:
         pickle.dump(usages, open(outputdir+w+'.pkl', mode='wb'))
         usages=[]
      print("done")

def retrieve_embeddings():
   tokenizer, model = load_model()
   inputdir='input_files/'
   outputdir = 'token_embeddings/'

   # read candidate lists for verbs and nouns
   # input method
   inputmethod = "pkl" #"file"
   if inputmethod == "file":
        verbes = {}
        with open('../collect_data/liste_candidats_verbes_vieilli.txt') as fin:
            for line in fin:
                a =  re.search(r"^([^_]+)_[0-9]", line)
                if a:
                    verbes[re.sub(r"\s*\*",'',a.group(1).strip())]="V"
                    #print(a.group(1))
        vlist = sorted(verbes, reverse=True)
   elif inputmethod == 'pkl':
        data = pickle.load(open("../contextual_embeddings/FrenchSemEval-1.1-191210/FSE-1.1.data.xmlverbs_sentence_nb.pkl", mode="rb"))
        #print(data)
        vlist = sorted(list(data.keys()),reverse=True)


   corpora = ['gallica','jsi']
   #vlist=['grève']
   # load sentences per year for each word in wordlist
   for w in vlist:
      w = w.strip()
      if os.path.isfile(outputdir+w+'.pkl'):
         print("already done :" + w)
         continue
      usages = []
      for corp in corpora:
         inputfile = inputdir+corp+'.'+w+'.csv'
         if os.path.isfile(inputfile) is False:
               print("No data for this word : " + w + ', ' + inputfile)
               continue
         print("Parsing : ", w, inputfile )
         df = pd.read_csv(inputfile)
         print(df.shape[0])
         df = df[df.key_word==w]
         data = df.to_records(index=False).tolist()
         print("Number of sentences with exact form : " + str(len(data)))
         datarow = (elt for elt in data if len(elt) == 3 and len(str(elt[0]))==4 and len(elt[1])>0 and len(elt[2])>0)
         i = 0
         for row in datarow:
            (vector, pos) = get_embeddings_iterator(row[2].lower(),row[1],model,tokenizer, debug=False)
            print(i)
            i =i+1
            if vector is False:
               print("Failure for sentence : " + row[1] + ', token : ' + row[2])
               continue
            usages.append((vector,row[2],row[1],pos,row[0]))
      # save tmp usages to already saved or create new pickle
      if len(usages)>0:
         pickle.dump(usages, open(outputdir+w+'.pkl', mode='wb'))
         usages=[]
      print("done")


def main_multiprocess():
   pool = mp.Pool(mp.cpu_count())
   # model and tokenizer initialized
   tokenizer, model = load_model()

   inputdir='input_files/'
   outputdir = 'token_embeddings/'

   # read candidate lists for verbs and nouns

   verbes = {}

   with open('../collect_data/liste_candidats_verbes_vieilli.txt') as fin:
      for line in fin:
         a =  re.search(r"^([^_]+)_[0-9]", line)
         if a:
               verbes[re.sub(r"\s*\*",'',a.group(1).strip())]="V"
               #print(a.group(1))
   vlist = sorted(verbes, reverse=True)

   corpora = ['gallica','jsi']
   vlist=['empêcher']
   # load sentences per year for each word in wordlist
   for w in vlist:
      w = w.strip()
      if os.path.isfile(outputdir+w+'.pkl'):
         print("already done :" + w)
         continue
      usages = []
      # pool callback function
      def collect_results(vector, token, sentence, position, year):
         if vector is False:
            print("No data for this sentence", token, sentence, year)
         else:
            usages.append((vector, token, sentence, position, year))

      for corp in corpora:
         inputfile = inputdir+corp+'.'+w+'.csv'
         if os.path.isfile(inputfile) is False:
               print("No data for this word : " + w + ', ' + inputfile)
               continue
         print("Parsing : ", w, inputfile )
         df = pd.read_csv(inputfile)
         print(df.shape[0])
         df = df[df.key_word==w]
         data = df.to_records(index=False).tolist()
         print("Number of sentences with exact form : " + str(len(data)))
         for i, elt in enumerate(data):
   #            if len(elt) == 3 and len(str(elt[0]))==4 and len(elt[1])>0 and len(elt[2])>0:
   #                sentence = re.sub(r"\b("+w+r")\b", r" \1 ", elt[1].lower())
   #                (vector, pos) = get_embeddings(elt[2].lower(),sentence,model,tokenizer, debug=False)
   #                if vector is False:
   #                    print("Failure for sentence : " + elt[1] + ', token : ' + elt[2])
   #                    continue
                  #print(i)
                  #usages.append((vector,elt[2],elt[1],pos,elt[0])) # (vector, token, sentence, position, year)
               if len(elt) == 3 and len(str(elt[0]))==4 and len(elt[1])>0 and len(elt[2])>0:
                  sentence = re.sub(r"\b("+w+r")\b", r" \1 ", elt[1].lower())
                  pool.apply_async(get_embeddings_parallel, args=(i, elt[2].lower(),sentence, elt[0], model,tokenizer), callback=collect_results)
         # Step 4: Close Pool and let all the processes complete    
         pool.close()
         pool.join()  # postpones the execution of next line of code until all processes in the queue are done.
      # save tmp usages to already saved or create new pickle
      if len(usages)>0:
         pickle.dump(usages, open(outputdir+w+'.pkl', mode='wb'))
         usages=[]
      print("done")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Missing argument. Add the task, either 'embed' or 'postag'")
        exit() 
    task= sys.argv[1]
    if task =='postag':
        tok, model = load_pos_tagger(model_name='gilf/french-postag-model')
        s = "Lagache, a tenu, en huit ans, plus de séances que le Conseil ï muni ci pal socialiste, ils ne parviennent qu'à faire hausser 10» épaules des gens sérieux"
        res = text_pos_tagging(s,tok,model)
        #print(res)
        #exit()
        analysis = []
        wordtmp=''
        cattmp=''
        for i, elt in enumerate(res):
            #print(i, len(res))
            if i < len(res)-1 and res[i+1]['word'].startswith("##"):
                if elt['word'].startswith("##"):
                    wordtmp += elt['word'][2:]
                else:
                    wordtmp += elt['word']
                cattmp +=  elt['entity_group']
            elif elt['word'].startswith("##"):
                analysis.append({'word': wordtmp+elt['word'][2:],'cat':elt['entity_group']})
                wordtmp=''
                cattmp=''
            else:
                analysis.append({'word': elt['word'],'cat':elt['entity_group']})
            #print(elt)
            #print(elt['entity_group'],elt['word'])
        
        for elt in analysis:
            print(elt)
        #main_generator_fct()
    elif task == 'embed':
        retrieve_embeddings()
    else:
        print("bad argument. Choose between 'embed' and 'postag' (given : " + task + ')' )