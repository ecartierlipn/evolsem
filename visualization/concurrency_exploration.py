import streamlit as st
#import plotly.figure_factory as ff
#import plotly.express as px
#import plotly.graph_objects as go
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.backends.backend_agg import RendererAgg
matplotlib.use("agg")
_lock = RendererAgg.lock
import numpy as np
from glob import glob
import re, os, sys
from transformers import pipeline
from transformers.pipelines import PipelineException
import traceback
import pickle
#import statistics
#from io import StringIO
# from https://towardsdatascience.com/7-reasons-why-you-should-use-the-streamlit-aggrid-component-2d9a2b6e32f0
from st_aggrid import AgGrid, JsCode,DataReturnMode,GridUpdateMode
from st_aggrid.grid_options_builder import GridOptionsBuilder

import udpipe_dependency_analysis as udpipe
import udapi
import udapi.core.node as node
from udapi.block.write.html import Html
#import udapi.block.util.filter as filter_udpipe
import streamlit.components.v1 as components
from subprocess import PIPE, run
#import pathlib
import udpipe_utils

# mysql
#import mysql.connector
#from mysql.connector import Error
#import traceback

# mysql connection parameters
host = 'localhost'
user = 'root'
password = 'neoveille'
db = 'evolsem'

def select_word_definition_from_mysql(word, table="wiktionary_lexicon", debug=False):
    '''
    '''
    try:
        conn = mysql.connector.connect(host=host,
                                       database=db,
                                       user=user,
                                       password=password,
                                       autocommit=True)
        if conn.is_connected():
            cursor = conn.cursor()
            q = 'select definition from ' + table + ' where word_lemma="' + word + '";'
            #log.info(q)
            cursor.execute(q)
            for row in cursor:
                #log.info(row)
                res = row[0]
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

# AG-grid display layout (javascript code as JsCode class)
html_jscode = JsCode("""
  function(params) {
      return "<div>"+params.value+"</div>";
  };
  """)


cellstyle_jscode = JsCode("""
function(params) {
        return {
            resizable: true,
            autoHeight: true,
            wrapText: true
        }
};
""")

jscodeRow = JsCode("""
            function(params) {
                if (params.data.spec === 1) {
                    return {
                        'color': 'white !important',
                        'backgroundColor': 'red !important'
                    }
                }
            };
            """)

jscode_rowformat = {
    "spec-style": 'data.spec == 1',
    "common-style": 'data.spec == 0',
}
jscode_rowformat_bk = {
    "spec-style": 'api.data.spec == 1',
    "common-style": 'api.data.spec == 0',
}

custom_css = {
    ".spec-style": {"background-color": "red !important"},
    ".common-style": {"background-color":'green !important'},#"color": "red !important",
}




def get_file_content_as_string(filename):
    with open(filename, mode="r") as f:
        contents = f.read()
        return contents

# load tokens
def load_tokens(word):
        df = pd.read_csv(wordsdic[word])
        tk = df["key_word"].value_counts().index.tolist()
        tk.insert(0,"Choose a token")
        return tk

# load sentences
def load_sentences(word, token=False):
        df = pd.read_csv(wordsdic[word])
        if token:
            s = df[df.key_word==token]["sentence"]
            if s.shape[0]> 100:
                s = s.sample(n=100, random_state=1).tolist()
        else:
            s = df["sentence"].sample(n=100, random_state=1).tolist()
        s.insert(0,"Choose a sentence")
        return s

@st.cache(allow_output_mutation=True)
def load_model(lang_model):
        model  = pipeline("fill-mask", model=lang_model)#, tokenizer="camembert-base"
        return model


# call id_sentences,global_pos,global_dep,internal_glob_pattern = get_dependency_analysis_components(wordsdic[word])
def get_dependency_analysis_components(word,wordfile):
            print(word)
            doc = udapi.Document(wordfile)
            # global variables
            id_sentences={}
            global_pos={}
            global_dep={}
            internal_glob_pattern=[]
            #print("*"*100,"\n")
            #print(wordfile,doc._highest_bundle_id, len(doc.bundles))
            for bundle in doc.bundles:
                #print(bundle.bundle_id)
                tree = bundle.get_tree()
                #print(len(tree))
                sent_id = bundle.bundle_id
                id_sentences[sent_id]=tree.compute_text()
                #print("*"*30,"[",word,"]")
                #print(sent_id,id_sentences[sent_id])
                for node in tree.descendants:
                        if node.form.lower() == word:
                            pos = node.upos
                            global_pos[pos] = global_pos.get(pos,0) + 1
                            dep = node.deprel
                            internal_pos_pattern = udpipe_utils.compute_internal_pattern(node,word,sent_id)
                            #print("*"*30,"[",word,"]")
                            #print(internal_pos_pattern)
                            if internal_pos_pattern:
                                internal_glob_pattern.append(internal_pos_pattern)
                            if pos =='VERB':
                                res = udpipe_utils.retrieve_external_patterns_verb(node,sent_id)# tree.compute_text()
                                if res:
                                    global_dep.setdefault('argumentative_structure',[]).append(res)
                                else:
                                    print("Problem with retrieve external pattern with this sentence :" + tree.compute_text())
                                res = udpipe_utils.retrieve_external_patterns_verb_conjrel(node,sent_id)# tree.compute_text()
                                if res:
                                    global_dep.setdefault('conjonctive_relation',[]).append(res)
                                else:
                                    print("Problem with retrieve external pattern with this sentence :" + tree.compute_text())

                            elif pos=='NOUN':    
                                res = udpipe_utils.retrieve_external_patterns_noun(node,sent_id)# tree.compute_text()
                                if res:                            
                                    global_dep.setdefault(dep,[]).append(res)
                                else:
                                    print("Problem with retrieve external pattern with this sentence :" + tree.compute_text())
                
            # save global_dep and internal_glob_pattern (for comparison JSI / Gallica)
            pickle.dump(global_dep, open(wordfile + '.global_dep.pkl',mode="wb"))
            pickle.dump(global_pos, open(wordfile + '.global_pos.pkl',mode="wb"))
            pickle.dump(id_sentences, open(wordfile + '.id_sentences.pkl',mode="wb"))
            pickle.dump(internal_glob_pattern, open(wordfile + '.internal_glob_pattern.pkl',mode="wb"))
            return id_sentences,global_pos,global_dep,internal_glob_pattern


# main
#definitions of protocols
dfdesc = pd.DataFrame([
                    ['XML-Roberta','XLM-R (XLM-RoBERTa) is a generic cross lingual sentence encoder that obtains state-of-the-art results on many cross-lingual understanding (XLU) benchmarks. It is trained on 2.5T of filtered CommonCrawl data in 100 languages. For details, see : https://github.com/pytorch/fairseq/tree/main/examples/xlmr'],
                    ['CamemBERT base','CamemBERT is a state-of-the-art language model for French based on the RoBERTa architecture pretrained on the French subcorpus of the newly available multilingual corpus OSCAR. For details, see : https://camembert-model.fr/'],
                    ['FlauBERT base','FlauBERT is a French BERT trained on a very large and heterogeneous French corpus. For details, see :  https://github.com/getalp/Flaubert'],
                    ['FastText model (sub-word Embeddings)','FastText is a sub-word embeddings enabling to represent even out-of-vocabulary lexemes by using subword information. Here we use the pretrained language model for French and a model trained on the Gallica corpus. For details, see :  https://fasttext.cc/docs/en/crawl-vectors.html (for Common Crawl French model) and https://arxiv.org/abs/1607.04606 (scientific paper)'],

                ], columns=['Model','Description'])


st.set_page_config(page_title="EvolSem",
                   page_icon="💡",layout="wide")

# bootstrap style
st.markdown('<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-1BmE4kWBq78iYhFldvKuhfTAU6auU8tT94WrHftjDbrCEXSU1oBoqyl2QvZ6jIW3" crossorigin="anonymous">', unsafe_allow_html=True)
            # bootstrap js to handle nav and other stuff
st.markdown('''
    <!-- jQuery first, then Popper.js, then Bootstrap JS -->
    <script src="https://code.jquery.com/jquery-3.2.1.slim.min.js" integrity="sha384-KJ3o2DKtIkvYIK3UENzmM7KCkRr/rE9/Qpg6aAZGJwFDMVNA/GpGFF93hXpG5KkN" crossorigin="anonymous"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/popper.js/1.12.9/umd/popper.min.js" integrity="sha384-ApNbgh9B+Y1QKtv3Rn7W3mgPxhU9K/ScQsAP7hUibX39j7fakFPskvXusvfa0b4Q" crossorigin="anonymous"></script>
    <script src="https://maxcdn.bootstrapcdn.com/bootstrap/4.0.0/js/bootstrap.min.js" integrity="sha384-JZR6Spejh4U02d8jOt6vLEHfe/JQGiRRSQQxSfFWpi1MquVdAyjUar5+76PVCmYl" crossorigin="anonymous"></script>
''',unsafe_allow_html=True)


padding = 4
st.markdown(f""" <style>
    .reportview-container .main .block-container{{
        padding-top: 0rem;
        padding-right: {padding}rem;
        padding-left: {padding}rem;
        padding-bottom: {padding}rem;
    }} 
    .css-1d391kg{{
        padding-top: 5rem; }} 
    .row-common {{
        font-weight: bold;
        background-color: #aa2e25 !important;
    }}
    .row-specific {{
        font-weight: bold;
        background-color: #357a38 !important;
    }}
    </style> """, unsafe_allow_html=True)

# CSS to inject contained in a string
hide_dataframe_row_index = """
            <style>
            .row_heading.level0 {display:none}
            .blank {display:none}
            </style>
            """

# Inject CSS with Markdown
#st.markdown(hide_dataframe_row_index, unsafe_allow_html=True)

# Side Bar #######################################################
#st.sidebar.header("Parameters")
st.title("EvolSem project : exploration of word meaning")
st.write("This web interface proposes to explore : 1/ Word and Contextual Embeddings Models capability to identify word meanings; 2/ Dependency analysis to get prototypical lexico-syntactic usage of a given lexeme. You can either explore specific sentences analysis or explore the meanings of a word globally. Please first choose a kind of exploration on the left panel.")
#with st.expander("More Information",expanded=False):
#    st.markdown(get_file_content_as_string("readme2.md"))
#    st.table(dfdesc)

analysis = st.sidebar.radio(
     "Choose a kind of exploration",
     ('Specific Sentence Analysis', 
     'Word/Contextual Embeddings (global)',
     'Dependency Analysis (global)'), index=1)

# specific word/sentence analysis
if analysis == 'Specific Sentence Analysis':
    
    # global variables for this case
    tokens=[]
    token="Choose a token"
    sentences=[]
    sentence="Choose a sentence"
    text_input=''

    # load lexem input files
    files = glob("input_files/*.csv")
    #print(files)   
    wordsdic = {f.split('/')[1].split('.')[1]:f for f in files}
    words = list(wordsdic.keys())
    #print(words)
    words.insert(0,"Choose a lexeme")

    lang_model = st.sidebar.selectbox(label="language model",
                                    options=['camembert-base','camembert/camembert-large','flaubert/flaubert_base_uncased','flaubert/flaubert_large_cased','xlm-roberta-large'])
    word = st.sidebar.selectbox(label="Lexeme",
                                    options=sorted(words))#'T-SNE (3d) - longer!',, 'LDA'

    # load model from the start
    model_load_state = st.text('Loading Model...')
    model = load_model(lang_model)
    # Notify the reader that the data was successfully loaded.
    model_load_state.text('')

    # events
    if word !="Choose a lexeme":
        tokens = load_tokens(word)
        token = st.sidebar.selectbox(label="Token",
                                        options=tokens)
    if token !="Choose a token":
        st.sidebar.info("Dictionaries")
        st.sidebar.markdown("https://www.cnrtl.fr/definition/"+word,unsafe_allow_html=True)
        st.sidebar.markdown("https://www.littre.org/definition/"+word,unsafe_allow_html=True)
        with st.sidebar.expander("Wiktionary"):
            components.iframe("https://fr.wiktionary.org/wiki/" + word + "#Français",height=400, scrolling=True)


        sentences = load_sentences(word, token)
        sentence = st.selectbox(label="Sentence",
                                        options=sentences)
        text_input = st.text_input('Or Enter a new sentence including the chosen token')


    if sentence != "Choose a sentence" or len(text_input)>0:
        if sentence != "Choose a sentence":
            text_input=''        
        if len(text_input)> 0:
            sentence = text_input        
        try:
            with st.spinner("Retrieving similar words for " + token + "(word:"+ word + ") in sentence " + sentence):
                #st.title("EvolSem project : exploration of word meaning through word and contextual embeddings")
                if lang_model.startswith("flaubert"):
                    sent = re.sub(token, "<special1>", sentence, count=1, flags=re.I)
                else:
                    sent = re.sub(token, "<mask>", sentence, count=1, flags=re.I)
                # token embeddings
                answers = model(sent)
                # build table for contextual embeddings fill-mask results
                html1 = '<table border="1" class="table"><thead><tr><th scope="col">Sentence</th><th scope="col">Score</th><th scope="col">Lexeme</th></tr></thead><tbody>'
                for ans in answers:
                    html1 = html1 + '<tr><td>' + re.sub(ans['token_str'],"<mark>"+ans['token_str']+"</mark>", ans['sequence'],count=1, flags=re.I)+'</td><td>'+ str(round(ans['score'],4))+ '</td><td>' + ans['token_str']+'</td></tr>'
                html1 = html1 + '</tbody></table>'
                # dependency analysis
                depana = udpipe.udpipe_analysis(sentence,tokenizer=True, tagger=True, parser=True)
                with open("udpipe_analysis.conllu", mode="w") as fout:
                    fout.write(depana['result'])
                write_html = Html(filehandle=open("udpipe_analysis-visu.html",mode="w"))#, docname_as_file=True
                doc = udapi.Document("./udpipe_analysis.conllu")
                #doc.draw()
                write_html.before_process_document(doc)
                write_html.process_document(doc)
                write_html.after_process_document(doc)
                with open("udpipe_analysis-visu.html") as fin:
                    html = fin.read()
                    javascript = '<script src="https://code.jquery.com/jquery-2.1.4.min.js"></script><script src="https://cdn.rawgit.com/eligrey/FileSaver.js/1.3.4/FileSaver.min.js"></script><script src="https://cdn.rawgit.com/ufal/js-treex-view/gh-pages/js-treex-view.js"></script>'
                    html = re.sub("^.+<body>",'',html)
                    html = re.sub("</body>.+$",'',html)
                    html = re.sub("tree\.svg",token+'.svg',html)
                    html = javascript + html

                components.html(
                    """
                    <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/4.0.0/css/bootstrap.min.css" integrity="sha384-Gn5384xqQ1aoWXA+058RXPxPg6fy4IWvTNh0E263XmFcJlSAwiGgFAW/dAiS6JXm" crossorigin="anonymous">
                    <script src="https://code.jquery.com/jquery-3.2.1.slim.min.js" integrity="sha384-KJ3o2DKtIkvYIK3UENzmM7KCkRr/rE9/Qpg6aAZGJwFDMVNA/GpGFF93hXpG5KkN" crossorigin="anonymous"></script>
                    <script src="https://maxcdn.bootstrapcdn.com/bootstrap/4.0.0/js/bootstrap.min.js" integrity="sha384-JZR6Spejh4U02d8jOt6vLEHfe/JQGiRRSQQxSfFWpi1MquVdAyjUar5+76PVCmYl" crossorigin="anonymous"></script>
                    <div id="accordion">
                    <div class="card">
                        <div class="card-header" id="headingOne">
                        <h5 class="mb-0">
                            <button class="btn btn-link" data-toggle="collapse" data-target="#collapseOne" aria-expanded="true" aria-controls="collapseOne">
                            Token Embeddings ("""+lang_model+""")
                            </button>
                        </h5>
                        </div>
                        <div id="collapseOne" class="collapse show" aria-labelledby="headingOne" data-parent="#accordion">
                        <div class="card-body">"""
                        + html1 +
                        """
                        </div>
                        </div>
                    </div>
                    <div class="card">
                        <div class="card-header" id="headingTwo">
                        <h5 class="mb-0">
                            <button class="btn btn-link" data-toggle="collapse" data-target="#collapseTwo" aria-expanded="true" aria-controls="collapseTwo">
                            Dependency Analysis (UDpipe)
                            </button>
                        </h5>
                        </div>
                        <div id="collapseTwo" class="collapse show" aria-labelledby="headingTwo" data-parent="#accordion">
                        <div class="card-body">"""
                        +html+
                        """
                            
                        </div>
                        </div>
                    </div>
                    </div>
                    """,
                    height=600,scrolling=True)
                #st.subheader("Local dependency tree")
                #st.json(res2)

        except PipelineException:
            st.warning("No **<mask>** Found in Input Sentence")
        except Exception as e:
            var = traceback.format_exc()
            st.warning("Error in : Model building. Error : \n" + var)                            

# overall analysis
elif analysis == 'Dependency Analysis (global)':
    # load preanalysed data per corpus.word
    files = glob("input_files/*.udpipe.conllu")
    #print(files) 
    # just wordlist to get words with data in both corpus
    wordlist = [f.split('/')[-1].split('.')[1] for f in files]
    #print(len(wordlist))
    wordlistboth = set([x for x in wordlist if wordlist.count(x) > 1])
    #print(sorted(wordlistboth),len(wordlistboth))
    wordlistone = set([x for x in wordlist if wordlist.count(x) == 1])
    #print(len(wordlistone))
    word = 'Choose a lexeme'
    corpusdic = {f.split('/')[-1].split('.')[0]:f for f in files}
    #print(wordlistone)
    #for k in wordlistone:
    #    print(corpusdic[k])
    corpora = list(corpusdic.keys())
    #print(words)
    allcorp = "+".join(corpora)
    corpora.insert(0,allcorp)
    corpora.insert(0,"Choose a corpus")
    corpus = st.sidebar.selectbox(label="Corpus",
                                    options=sorted(corpora))
    if corpus != 'Choose a corpus' and word=="Choose a lexeme":
        #print("if branch. Corpus : " + corpus + ", word : " + word)
        if re.search('\+',corpus):
            #print("both corpora")            
            words = list(wordlistboth)
            words.insert(0,"Choose a lexeme")
            word = st.sidebar.selectbox(label="Lexeme",
                                            options=sorted(words))
        else:
            files = [f for f in files if re.search(corpus, f)]
            wordsdic = {f.split('/')[-1].split('.')[1]:f for f in files}
            words = list(wordsdic.keys())
            words.insert(0,"Choose a lexeme")
            word = st.sidebar.selectbox(label="Lexeme",
                                            options=sorted(words))
    if word != 'Choose a lexeme' and corpus != 'Choose a corpus':
        st.sidebar.info("Dictionaries")
        st.sidebar.markdown("https://www.cnrtl.fr/definition/"+word,unsafe_allow_html=True)
        st.sidebar.markdown("https://www.littre.org/definition/"+word,unsafe_allow_html=True)
        with st.sidebar.expander("Wiktionary"):
            components.iframe("https://fr.wiktionary.org/wiki/" + word+ "#Français",height=400, scrolling=True)


        if re.search('\+',corpus):
            id_sentences1,global_pos1,global_dep1,internal_glob_pattern1 = get_dependency_analysis_components(word, "input_files/gallica." +word+".csv.udpipe.conllu")
            id_sentences2,global_pos2,global_dep2,internal_glob_pattern2 = get_dependency_analysis_components(word, "input_files/jsi." +word+".csv.udpipe.conllu")
            total_sent1 = sum(list(global_pos1.values()))
            total_sent2 = sum(list(global_pos2.values()))

            with st.expander("Internal Dependency Structure"):
                #st.info("This section presents the most frequent linear structure around the focus word (limited to 3 token left and right).")
                col1, col2  = st.columns(2)
                with col1:
                    st.info("Gallica data ("+ str(total_sent1) + " sentences)")
                    # display part-of-speech distribution
                    sorted_global_pos1 = {}
                    global_pos1['ALL POS']= total_sent1
                    sorted_keys = sorted(global_pos1, key=global_pos1.get, reverse=True)  # [1, 3, 2]
                    for w in sorted_keys:
                        sorted_global_pos1[w] = global_pos1[w]                    
                    pos = st.selectbox(label="Part-of-speech",
                                            options=sorted_global_pos1, format_func=lambda x : x + '(' + str(sorted_global_pos1[x]) + ')')
                    #st.selectb
                    #st.write(sorted(global_pos1,key=lambda x : global_pos1[x], reverse=True))
                    print(internal_glob_pattern1)
                    if pos != 'ALL POS':
                        internal_glob_pattern1 = [info for info in internal_glob_pattern1 if info['word_pos']==pos]
                    df_depint1 = pd.DataFrame(internal_glob_pattern1)
                    print(df_depint1.info())
                    df_depint1['id_sent']= df_depint1.apply(lambda x : re.sub(word, '<mark>' + word + '</mark>', id_sentences1[x['id_sent']], flags=re.I), axis=1)
                    gbint = GridOptionsBuilder.from_dataframe(df_depint1)
                    return_mode_value = DataReturnMode.__members__['FILTERED']
                    update_mode_value = GridUpdateMode.__members__['MODEL_CHANGED']            
                    gbint.configure_pagination()
                    gbint.configure_default_column(groupable=True, value=True, enableRowGroup=True, aggFunc='count', editable=False)
                    gbint.configure_column('lemma', rowGroup=True, sort="desc")
                    gbint.configure_column("id_sent", wrapText=True, flex=2, cellRenderer=html_jscode, autoHeight=True, width=700) # , cellStyle=cellstyle_jscode , , cellStyle={"resizable": True,"autoHeight": True,"wrapText": True}
                    gbint.configure_side_bar()
                    gbint.configure_selection("single")
                    gridOptions = gbint.build()
                    ag_resp2int = AgGrid(
                                    df_depint1, 
                                    data_return_mode=return_mode_value, 
                                    update_mode=update_mode_value,
                                    fit_columns_on_grid_load=True,                
                                    gridOptions=gridOptions, 
                                    allow_unsafe_jscode=True,
                                    height=500,
                                    enable_enterprise_modules=True
                                    )#, enable_enterprise_modules=True
                    selected_sent_int = ag_resp2int['selected_rows']
                    if len(selected_sent_int)==1:
                        sentence = re.sub(r"<mark>|</mark>","", selected_sent_int[0]['id_sent'])
                        depana = udpipe.udpipe_analysis(sentence,tokenizer=True, tagger=True, parser=True)
                        with open("udpipe_analysis.conllu", mode="w") as fout:
                            fout.write(depana['result'])
                        write_html = Html(filehandle=open("udpipe_analysis-visu.html",mode="w"))#, docname_as_file=True
                        doc = udapi.Document("./udpipe_analysis.conllu")
                        write_html.before_process_document(doc)
                        write_html.process_document(doc)
                        write_html.after_process_document(doc)
                        #components.iframe("udpipe_analysis-visu.html", height=600, scrolling=True)
                        with open("udpipe_analysis-visu.html") as fin:
                            html = fin.read()
                            javascript = '<script src="https://code.jquery.com/jquery-2.1.4.min.js"></script><script src="https://cdn.rawgit.com/eligrey/FileSaver.js/1.3.4/FileSaver.min.js"></script><script src="https://cdn.rawgit.com/ufal/js-treex-view/gh-pages/js-treex-view.js"></script>'
                            html = re.sub("^.+<body>",'',html)
                            html = re.sub("</body>.+$",'',html)
                            html = javascript + html
                            components.html(html, height=600, scrolling=True)

                with col2:
                    st.info("JSI data ("+ str(sum(list(global_pos2.values()))) + " sentences)")
                    #st.write(global_pos2)
                    # display part-of-speech distribution
                    sorted_global_pos2 = {}
                    global_pos2['ALL POS']= total_sent2
                    sorted_keys = sorted(global_pos2, key=global_pos2.get, reverse=True)  # [1, 3, 2]
                    for w in sorted_keys:
                        sorted_global_pos2[w] = global_pos2[w]                    
                    pos = st.selectbox(label="Part-of-speech",
                                            options=sorted_global_pos2, format_func=lambda x : x + '(' + str(sorted_global_pos2[x]) + ')')
                    #st.selectb
                    #st.write(sorted(global_pos1,key=lambda x : global_pos1[x], reverse=True))
                    #print(internal_glob_pattern2)
                    if pos != 'ALL POS':
                        internal_glob_pattern2 = [info for info in internal_glob_pattern2 if info['word_pos']==pos]

                    df_depint2 = pd.DataFrame(internal_glob_pattern2)
                    print(df_depint2.info())
                    df_depint2['id_sent']= df_depint2.apply(lambda x : re.sub(word, '<mark>' + word + '</mark>', id_sentences2[x['id_sent']], flags=re.I), axis=1)
                    gbint2 = GridOptionsBuilder.from_dataframe(df_depint2)
                    return_mode_value = DataReturnMode.__members__['FILTERED']
                    update_mode_value = GridUpdateMode.__members__['MODEL_CHANGED']            
                    gbint2.configure_pagination()
                    gbint2.configure_default_column(groupable=True, value=True, enableRowGroup=True, aggFunc='count', editable=False)
                    gbint2.configure_column('lemma', rowGroup=True, sort="desc")
                    gbint2.configure_column("id_sent", wrapText=True, flex=2, cellRenderer=html_jscode, autoHeight=True, width=700) # , cellStyle=cellstyle_jscode , , cellStyle={"resizable": True,"autoHeight": True,"wrapText": True}
                    gbint2.configure_side_bar()
                    gbint2.configure_selection("single")
                    gridOptions2 = gbint2.build()
                    ag_resp2int2 = AgGrid(
                                    df_depint2, 
                                    data_return_mode=return_mode_value, 
                                    update_mode=update_mode_value,
                                    fit_columns_on_grid_load=True,                
                                    gridOptions=gridOptions2, 
                                    allow_unsafe_jscode=True,
                                    height=500,
                                    enable_enterprise_modules=True
                                    )#, enable_enterprise_modules=True
                    selected_sent_int2 = ag_resp2int2['selected_rows']
                    if len(selected_sent_int2)==1:
                        sentence = re.sub(r"<mark>|</mark>","", selected_sent_int2[0]['id_sent'])
                        depana = udpipe.udpipe_analysis(sentence,tokenizer=True, tagger=True, parser=True)
                        with open("udpipe_analysis.conllu", mode="w") as fout:
                            fout.write(depana['result'])
                        write_html = Html(filehandle=open("udpipe_analysis-visu.html",mode="w"))#, docname_as_file=True
                        doc = udapi.Document("./udpipe_analysis.conllu")
                        write_html.before_process_document(doc)
                        write_html.process_document(doc)
                        write_html.after_process_document(doc)
                        #components.iframe("udpipe_analysis-visu.html", height=600, scrolling=True)
                        with open("udpipe_analysis-visu.html") as fin:
                            html = fin.read()
                            javascript = '<script src="https://code.jquery.com/jquery-2.1.4.min.js"></script><script src="https://cdn.rawgit.com/eligrey/FileSaver.js/1.3.4/FileSaver.min.js"></script><script src="https://cdn.rawgit.com/ufal/js-treex-view/gh-pages/js-treex-view.js"></script>'
                            html = re.sub("^.+<body>",'',html)
                            html = re.sub("</body>.+$",'',html)
                            html = javascript + html
                            components.html(html, height=600, scrolling=True)

            with st.expander("External Dependency Structure"):
                # compare lexico-syntactic patterns ("argumentative patterns")
                if 'argumentative_structure' in global_dep2:                       
                    jsidep = [elt['lemma'] for elt in global_dep2['argumentative_structure']]
                else:
                    jsidep = [elt['lemma'] for k in global_dep2 for elt in global_dep2[k]]
                jsidep2 = { i : jsidep.count(i) for i in jsidep if jsidep.count(i) > 5 }
                if 'argumentative_structure' in global_dep1:  
                    gallicadep = [elt['lemma'] for elt in global_dep1['argumentative_structure']]
                else:
                    gallicadep = [elt['lemma'] for k in global_dep1 for elt in global_dep1[k]]
                gallicadep2 = { i : gallicadep.count(i) for i in gallicadep if gallicadep.count(i) > 5 }
                gallica_spec = set(gallicadep2.keys()).difference(set(jsidep2.keys()))
                jsi_spec = set(jsidep2.keys()).difference(set(gallicadep2.keys()))
                common = set(gallicadep2.keys()).intersection(set(jsidep2.keys()))
                st.write(gallica_spec)
                st.write(jsi_spec)
                st.write(common)

                col3,col4 = st.columns(2)
                with col3:
                    st.info("Gallica data ("+ str(total_sent1) + " sentences)")

                    #st.info("This section presents the external argumental structure of Nouns and Verbs derived from dependency analysis (UDPipe). For Verbs, core argument structure (Subject, Object, Indirect Object and Oblique), conjonctive relations (verb and verb) and copulative/definitory structure (Verb means X, verb, it's X, etc. )  are proposed. For Nouns, we focus on Subject, Object, Indirect Object, Oblique, Conjonctive and copulative structures.")
                    #st.write(global_dep)
                    global_dep_synth = {dep:len(global_dep1[dep]) for dep in global_dep1}
                    dependency_relations = sorted(global_dep_synth, key=global_dep_synth.get, reverse=True)
                    #dependency_relations = list(global_dep.keys())
                    dependency_relations.insert(0,"Choose a dependency relation")
                    dep_relation = st.selectbox(label="",options=dependency_relations, format_func=lambda x : x + " (" + str(len(global_dep1[x]))+") - "+ udpipe_utils.udeprel_def[x] if x in global_dep1 and x in udpipe_utils.udeprel_def else x)

                    if dep_relation != "Choose a dependency relation":
                        df_dep = pd.DataFrame(global_dep1[dep_relation])
                        df_dep['spec'] = np.where(df_dep['lemma'].isin(gallica_spec), 'specific', 'common')
                        print(df_dep.info())
                        print(df_dep.spec.value_counts())
                        df_dep['id_sent']= df_dep.apply(lambda x : re.sub(word, '<mark>' + word + '</mark>', id_sentences1[x['id_sent']], flags=re.I), axis=1)
                        #df_dep['id_sent']= df_dep.apply(lambda x : re.sub(r"("+ x['form'].replace('(','\(').replace(')','\)')+ '|'+ word + ')', r"<mark>\1</mark>", x['id_sent']), axis=1)
                        #df_dep['id_sent']= df_dep.apply(lambda x : re.sub(r"("+ "|".join(x['form'].split(" "))+ '|'+ word + ')', r"<mark>\1</mark>", x['id_sent']), axis=1)
                        gb = GridOptionsBuilder.from_dataframe(df_dep)

                        return_mode_value = DataReturnMode.__members__['FILTERED']
                        update_mode_value = GridUpdateMode.__members__['MODEL_CHANGED']            
                        gb.configure_pagination()
                        gb.configure_default_column(groupable=True, value=True, enableRowGroup=True, aggFunc='count', editable=False)
                        gb.configure_column('lemma', rowGroup=True, sort="desc")
                        gb.configure_column("id_sent", wrapText=True, flex=2, cellRenderer=html_jscode, autoHeight=True, width=700) # , cellStyle=cellstyle_jscode , , cellStyle={"resizable": True,"autoHeight": True,"wrapText": True}
                        gb.configure_side_bar()
                        gb.configure_selection("single")
                        #gb.configure_grid_options(rowClassRules = jscode_rowformat)
                        #gb.configure_grid_options(getRowStyle = jscodeRow)
                        gridOptions = gb.build()
                        #gridOptions['getRowStyle']= jscodeRow
                        ag_resp2 = AgGrid(
                                    df_dep, 
                                    data_return_mode=return_mode_value, 
                                    update_mode=update_mode_value,
                                    fit_columns_on_grid_load=True,                
                                    gridOptions=gridOptions, 
                                    allow_unsafe_jscode=True,
                                    custom_css=custom_css,
                                    height=500,
                                    enable_enterprise_modules=True
                                    )
                        selected_sent = ag_resp2['selected_rows']
                        if len(selected_sent)==1:
                                print("sentence", selected_sent,selected_sent[0]['id_sent'])
                                sentence = re.sub(r"<mark>|</mark>","", selected_sent[0]['id_sent'])
                                depana = udpipe.udpipe_analysis(sentence,tokenizer=True, tagger=True, parser=True)
                                with open("udpipe_analysis.conllu", mode="w") as fout:
                                    fout.write(depana['result'])
                                write_html = Html(filehandle=open("udpipe_analysis-visu.html",mode="w"))#, docname_as_file=True
                                doc = udapi.Document("./udpipe_analysis.conllu")
                                write_html.before_process_document(doc)
                                write_html.process_document(doc)
                                write_html.after_process_document(doc)
                                with open("udpipe_analysis-visu.html") as fin:
                                    html = fin.read()
                                    javascript = '<script src="https://code.jquery.com/jquery-2.1.4.min.js"></script><script src="https://cdn.rawgit.com/eligrey/FileSaver.js/1.3.4/FileSaver.min.js"></script><script src="https://cdn.rawgit.com/ufal/js-treex-view/gh-pages/js-treex-view.js"></script>'
                                    html = re.sub("^.+<body>",'',html)
                                    html = re.sub("</body>.+$",'',html)
                                    html = javascript + html
                                    components.html(html, height=600, scrolling=True)
                with col4:
                    st.info("JSI data ("+ str(total_sent2) + " sentences)")

                    #st.info("This section presents the external argumental structure of Nouns and Verbs derived from dependency analysis (UDPipe). For Verbs, core argument structure (Subject, Object, Indirect Object and Oblique), conjonctive relations (verb and verb) and copulative/definitory structure (Verb means X, verb, it's X, etc. )  are proposed. For Nouns, we focus on Subject, Object, Indirect Object, Oblique, Conjonctive and copulative structures.")
                    #st.write(global_dep)
                    global_dep_synth2 = {dep:len(global_dep2[dep]) for dep in global_dep2}
                    dependency_relations2 = sorted(global_dep_synth2, key=global_dep_synth2.get, reverse=True)
                    #dependency_relations = list(global_dep.keys())
                    dependency_relations2.insert(0,"Choose a dependency relation")
                    dep_relation2 = st.selectbox(label="",options=dependency_relations2, format_func=lambda x : x + " (" + str(len(global_dep2[x]))+") - "+ udpipe_utils.udeprel_def[x] if x in global_dep2 and x in udpipe_utils.udeprel_def else x)

                    if dep_relation2 != "Choose a dependency relation":
                        df_dep2 = pd.DataFrame(global_dep2[dep_relation2])
                        df_dep2['spec'] = np.where(df_dep2['lemma'].isin(jsi_spec), 'specific', 'common')

                        print(df_dep2.info())
                        df_dep2['id_sent']= df_dep2.apply(lambda x : re.sub(word, '<mark>' + word + '</mark>', id_sentences2[x['id_sent']], flags=re.I), axis=1)
                        #df_dep['id_sent']= df_dep.apply(lambda x : re.sub(r"("+ x['form'].replace('(','\(').replace(')','\)')+ '|'+ word + ')', r"<mark>\1</mark>", x['id_sent']), axis=1)
                        #df_dep['id_sent']= df_dep.apply(lambda x : re.sub(r"("+ "|".join(x['form'].split(" "))+ '|'+ word + ')', r"<mark>\1</mark>", x['id_sent']), axis=1)
                        gb2 = GridOptionsBuilder.from_dataframe(df_dep2)

                        return_mode_value = DataReturnMode.__members__['FILTERED']
                        update_mode_value = GridUpdateMode.__members__['MODEL_CHANGED']            
                        gb2.configure_pagination()
                        #gb2.configure_column
                        gb2.configure_default_column(groupable=True, value=True, enableRowGroup=True, aggFunc='count', editable=False)
                        gb2.configure_column('lemma', rowGroup=True, sort="desc")
                        gb2.configure_column(0, width=700)
                        gb2.configure_column("id_sent", wrapText=True, flex=2, cellRenderer=html_jscode, autoHeight=True, width=700) # , cellStyle=cellstyle_jscode , , cellStyle={"resizable": True,"autoHeight": True,"wrapText": True}
                        gb2.configure_side_bar()
                        gb2.configure_selection("single")
                        gridOptions2 = gb2.build()
                        ag_resp3 = AgGrid(
                                    df_dep2, 
                                    data_return_mode=return_mode_value, 
                                    update_mode=update_mode_value,
                                    fit_columns_on_grid_load=True,                
                                    gridOptions=gridOptions, 
                                    allow_unsafe_jscode=True,
                                    height=500,
                                    enable_enterprise_modules=True
                                    )
                        selected_sent2 = ag_resp3['selected_rows']
                        if len(selected_sent2)==1:
                                print("sentence", selected_sent2,selected_sent2[0]['id_sent'])
                                sentence2 = re.sub(r"<mark>|</mark>","", selected_sent2[0]['id_sent'])
                                depana = udpipe.udpipe_analysis(sentence2,tokenizer=True, tagger=True, parser=True)
                                with open("udpipe_analysis.conllu", mode="w") as fout:
                                    fout.write(depana['result'])
                                write_html = Html(filehandle=open("udpipe_analysis-visu.html",mode="w"))#, docname_as_file=True
                                doc = udapi.Document("./udpipe_analysis.conllu")
                                write_html.before_process_document(doc)
                                write_html.process_document(doc)
                                write_html.after_process_document(doc)
                                with open("udpipe_analysis-visu.html") as fin:
                                    html = fin.read()
                                    javascript = '<script src="https://code.jquery.com/jquery-2.1.4.min.js"></script><script src="https://cdn.rawgit.com/eligrey/FileSaver.js/1.3.4/FileSaver.min.js"></script><script src="https://cdn.rawgit.com/ufal/js-treex-view/gh-pages/js-treex-view.js"></script>'
                                    html = re.sub("^.+<body>",'',html)
                                    html = re.sub("</body>.+$",'',html)
                                    html = javascript + html
                                    components.html(html, height=600, scrolling=True)
        
        # fake condition : does not work (with function to get dependency info)
        elif True:#re.search('toto',corpus)
            word = word.strip()
            print(word,wordsdic[word])
            id_sentences,global_pos,global_dep,internal_glob_pattern = get_dependency_analysis_components(word,wordsdic[word])
            #print(id_sentences, global_pos, global_dep, internal_glob_pattern)
            #with st.expander("Linear structure analysis (to be done)"):
            #    st.info("This section presents the most frequent linear structure around the focus word (limited to 3 token left and right).")

            with st.expander("Internal Dependency Structure"):
                st.info("This section presents the internal structure of Nouns and Verbs derived from dependency analysis (UDPipe). For Nouns, Noun + ADJ, ADJ + NOUN, NOUN PREP NOUN, NOUN + PROPREL and other internal structures are proposed. For Verbs, internal flexional structure is proposed, as well as auxiliary and modal structures.")
                st.write(global_pos)

                df_depint = pd.DataFrame(internal_glob_pattern)
                print(df_depint.info())
                #print(id_sentences)
                df_depint['id_sent']= df_depint.apply(lambda x : re.sub(word, '<mark>' + word + '</mark>', id_sentences[x['id_sent']], flags=re.I), axis=1)
                gbint = GridOptionsBuilder.from_dataframe(df_depint)
                return_mode_value = DataReturnMode.__members__['FILTERED']
                update_mode_value = GridUpdateMode.__members__['MODEL_CHANGED']            
                gbint.configure_pagination()
                gbint.configure_default_column(groupable=True, value=True, enableRowGroup=True, aggFunc='count', editable=False)
                gbint.configure_column('lemma', rowGroup=True, sort="desc")
                gbint.configure_column("id_sent", wrapText=True, flex=2, cellRenderer=html_jscode, autoHeight=True, width=700) # , cellStyle=cellstyle_jscode , , cellStyle={"resizable": True,"autoHeight": True,"wrapText": True}
                gbint.configure_side_bar()
                gbint.configure_selection("single")
                gridOptions = gbint.build()
                ag_resp2int = AgGrid(
                                df_depint, 
                                data_return_mode=return_mode_value, 
                                update_mode=update_mode_value,
                                fit_columns_on_grid_load=True,                
                                gridOptions=gridOptions, 
                                allow_unsafe_jscode=True,
                                height=500,
                                enable_enterprise_modules=True
                                )#, enable_enterprise_modules=True
                selected_sent_int = ag_resp2int['selected_rows']
                if len(selected_sent_int)==1:
                    sentence = re.sub(r"<mark>|</mark>","", selected_sent_int[0]['id_sent'])
                    depana = udpipe.udpipe_analysis(sentence,tokenizer=True, tagger=True, parser=True)
                    with open("udpipe_analysis.conllu", mode="w") as fout:
                        fout.write(depana['result'])
                    write_html = Html(filehandle=open("udpipe_analysis-visu.html",mode="w"))#, docname_as_file=True
                    doc = udapi.Document("./udpipe_analysis.conllu")
                    write_html.before_process_document(doc)
                    write_html.process_document(doc)
                    write_html.after_process_document(doc)
                    #components.iframe("udpipe_analysis-visu.html", height=600, scrolling=True)
                    with open("udpipe_analysis-visu.html") as fin:
                        html = fin.read()
                        javascript = '<script src="https://code.jquery.com/jquery-2.1.4.min.js"></script><script src="https://cdn.rawgit.com/eligrey/FileSaver.js/1.3.4/FileSaver.min.js"></script><script src="https://cdn.rawgit.com/ufal/js-treex-view/gh-pages/js-treex-view.js"></script>'
                        html = re.sub("^.+<body>",'',html)
                        html = re.sub("</body>.+$",'',html)
                        html = javascript + html
                        components.html(html, height=600, scrolling=True)

            with st.expander("External Dependency Structure"):
                #st.subheader("External Dependency Structure")
                st.info("This section presents the external argumental structure of Nouns and Verbs derived from dependency analysis (UDPipe). For Verbs, core argument structure (Subject, Object, Indirect Object and Oblique), conjonctive relations (verb and verb) and copulative/definitory structure (Verb means X, verb, it's X, etc. )  are proposed. For Nouns, we focus on Subject, Object, Indirect Object, Oblique, Conjonctive and copulative structures.")
                #st.write(global_dep)
                global_dep_synth = {dep:len(global_dep[dep]) for dep in global_dep}
                dependency_relations = sorted(global_dep_synth, key=global_dep_synth.get, reverse=True)
                #dependency_relations = list(global_dep.keys())
                dependency_relations.insert(0,"Choose a dependency relation")
                dep_relation = st.selectbox(label="",options=dependency_relations, format_func=lambda x : x + " (" + str(len(global_dep[x]))+") - "+ udpipe_utils.udeprel_def[x] if x in global_dep and x in udpipe_utils.udeprel_def else x)

                if dep_relation != "Choose a dependency relation":
                    df_dep = pd.DataFrame(global_dep[dep_relation])
                    print(df_dep.info())
                    df_dep['id_sent']= df_dep.apply(lambda x : re.sub(word, '<mark>' + word + '</mark>', id_sentences[x['id_sent']], flags=re.I), axis=1)
                    #df_dep['id_sent']= df_dep.apply(lambda x : re.sub(r"("+ x['form'].replace('(','\(').replace(')','\)')+ '|'+ word + ')', r"<mark>\1</mark>", x['id_sent']), axis=1)
                    #df_dep['id_sent']= df_dep.apply(lambda x : re.sub(r"("+ "|".join(x['form'].split(" "))+ '|'+ word + ')', r"<mark>\1</mark>", x['id_sent']), axis=1)
                    gb = GridOptionsBuilder.from_dataframe(df_dep)

                    return_mode_value = DataReturnMode.__members__['FILTERED']
                    update_mode_value = GridUpdateMode.__members__['MODEL_CHANGED']            
                    gb.configure_pagination()
                    gb.configure_default_column(groupable=True, value=True, enableRowGroup=True, aggFunc='count', editable=False)
                    gb.configure_column('lemma', rowGroup=True, sort="desc")
                    gb.configure_column("id_sent", wrapText=True, flex=2, cellRenderer=html_jscode, autoHeight=True, width=700) # , cellStyle=cellstyle_jscode , , cellStyle={"resizable": True,"autoHeight": True,"wrapText": True}
                    gb.configure_side_bar()
                    gb.configure_selection("single")
                    gridOptions = gb.build()
                    ag_resp2 = AgGrid(
                                df_dep, 
                                data_return_mode=return_mode_value, 
                                update_mode=update_mode_value,
                                fit_columns_on_grid_load=True,                
                                gridOptions=gridOptions, 
                                allow_unsafe_jscode=True,
                                height=500,
                                enable_enterprise_modules=True
                                )
                    selected_sent = ag_resp2['selected_rows']
                    if len(selected_sent)==1:
                            sentence = re.sub(r"<mark>|</mark>","", selected_sent[0]['id_sent'])
                            depana = udpipe.udpipe_analysis(sentence,tokenizer=True, tagger=True, parser=True)
                            with open("udpipe_analysis.conllu", mode="w") as fout:
                                fout.write(depana['result'])
                            write_html = Html(filehandle=open("udpipe_analysis-visu.html",mode="w"))#, docname_as_file=True
                            doc = udapi.Document("./udpipe_analysis.conllu")
                            write_html.before_process_document(doc)
                            write_html.process_document(doc)
                            write_html.after_process_document(doc)
                            with open("udpipe_analysis-visu.html") as fin:
                                html = fin.read()
                                javascript = '<script src="https://code.jquery.com/jquery-2.1.4.min.js"></script><script src="https://cdn.rawgit.com/eligrey/FileSaver.js/1.3.4/FileSaver.min.js"></script><script src="https://cdn.rawgit.com/ufal/js-treex-view/gh-pages/js-treex-view.js"></script>'
                                html = re.sub("^.+<body>",'',html)
                                html = re.sub("</body>.+$",'',html)
                                html = javascript + html
                                components.html(html, height=600, scrolling=True)



# overall analysis
elif analysis == 'Word/Contextual Embeddings (global)':
    # load preanalysed data per corpus.word
    files = glob("input_files/*.fill_mask.pkl")
    print(files) 
    # just wordlist to get words with data in both corpus
    wordlist = [f.split('/')[-1].split('.')[1] for f in files]
    wordlistboth = set([x for x in wordlist if wordlist.count(x) > 1])
    word = 'Choose a lexeme'
    corpusdic = {f.split('/')[-1].split('.')[0]:f for f in files}
    corpora = list(corpusdic.keys())
    modelsdic = {f.split('/')[-1].split('.')[3]:1 for f in files}
    models = list(modelsdic.keys())
    #print(words)
    if len(corpora)>1:
        allcorp = "+".join(corpora)
        corpora.insert(0,allcorp)
    corpora.insert(0,"Choose a corpus")

    corpus = st.sidebar.selectbox(label="Corpus",
                                    options=sorted(corpora))
    embed_model = st.sidebar.selectbox(label="Modèle",
                                    options=sorted(models))

    if corpus != 'Choose a corpus' and word=="Choose a lexeme":
        #print("if branch. Corpus : " + corpus + ", word : " + word)
        if re.search('\+',corpus):
            #print("both corpora")            
            words = list(wordlistboth)
            words.insert(0,"Choose a lexeme")
            word = st.sidebar.selectbox(label="Lexeme",
                                            options=sorted(words))
        else:
            files = [f for f in files if re.search(corpus, f)]
            wordsdic = {f.split('/')[-1].split('.')[1]:f for f in files}
            words = list(wordsdic.keys())
            words.insert(0,"Choose a lexeme")
            word = st.sidebar.selectbox(label="Lexeme",
                                            options=sorted(words))
    if word != 'Choose a lexeme' and corpus != 'Choose a corpus':
        st.sidebar.info("Dictionaries")
        st.sidebar.markdown("https://www.cnrtl.fr/definition/"+word,unsafe_allow_html=True)
        st.sidebar.markdown("https://www.littre.org/definition/"+word,unsafe_allow_html=True)
        with st.sidebar.expander("Wiktionary"):
            components.iframe("https://fr.wiktionary.org/wiki/" + word+ "#Français",height=400, scrolling=True)
        
        # both corpora
        if re.search('\+',corpus):
            #st.subheader("Work in progress....")
            ## word embeddings
            with st.expander("Word embeddings"):
                st.info("The lexems below are the result of the word embeddings with Word2Vec, either the pretrained model for the recent period (from FrWac with lemmatization), either a trained model on a Gallica Press corpous (1850-1930)")

                word_embs = pickle.load(open("./input_files/word2vec.jsi.evolsem_words.pkl", mode="rb"))
                word_embs2 = pickle.load(open("./input_files/word2vec.gallica.evolsem_words.pkl", mode="rb"))
#                word_embs = pickle.load(open("./input_files/fasttext.cc.fr.300.bin.evolsem_words.pkl", mode="rb"))
#                word_embs2 = pickle.load(open("./input_files/fasttext.fasttext.gallica_corpus.cbow.bin.evolsem_words.pkl", mode="rb"))
                col3,col4 = st.columns(2)
                with col3 :
                    st.subheader("1850-1930")
                    if word in word_embs2:
                        df1 = pd.DataFrame(word_embs2[word], columns=['score','word']).reset_index(drop=True)
                        st.dataframe(df1, width=300)
                        #st.json(word_embs2[word])
                    else:
                        st.write("No word embeddings for this word")
                with col4:
                    st.subheader("2000-2020")
                    if word in word_embs:
                        df = pd.DataFrame(word_embs[word], columns=['score','word']).reset_index(drop=True)
                        st.dataframe(df, width=300)
                        #st.json(word_embs[word])
                    else:
                        st.write("No word embeddings for this word")


            # Contextual embeddings
            data1 = pickle.load(open("input_files/gallica."+word+ ".csv."+embed_model+ ".fill_mask.pkl",mode="rb"))
            data1count = 0
            for k in data1.keys():
                data1count += len(data1[k]) 
            data2 = pickle.load(open("input_files/jsi."+word+ ".csv."+embed_model+ ".fill_mask.pkl",mode="rb"))
            data2count = 0
            for k in data2.keys():
                data2count += len(data2[k]) 
            #print(data1)
            with st.expander("Contextual embeddings"):
                col3,col4 = st.columns(2)
                with col3:
                    st.info("Gallica data ("+ str(len(data1)) + " words for " + str(data1count) + " sentences)")

                    #st.info("The lexems below are the result of the fill-mask process applied to all sentences for the main lexem. Number of sentences for which they appear, and average score is given. By selecting a row, you will acess to the sentences and the score of the lexem.")
                    #st.markdown("**Word : " + word + ", Corpus : "+ corpus + ", Language model : " + embed_model + "**")
                    
                    # ag grid
                    ord_dict = [{"lexeme":tok.lower(), "score" : round(sent_score[1],5), "sentence": re.sub('<mask>', '<mark>'+word+'</mark>',sent_score[0])}  for tok in data1 for sent_score in data1[tok]]
                    df = pd.DataFrame(ord_dict)
                    # first datagrid
                    gb = GridOptionsBuilder.from_dataframe(df)
                    return_mode_value = DataReturnMode.__members__['FILTERED']
                    update_mode_value = GridUpdateMode.__members__['MODEL_CHANGED']            
                    gb.configure_pagination()
                    gb.configure_default_column(groupable=True, value=True, enableRowGroup=True, aggFunc='count', editable=False)
                    gb.configure_column('lexeme', rowGroup=True, sort="desc")
                    gb.configure_column('score', aggFunc="avg")
                    gb.configure_column("sentence", wrapText=True, flex=2, cellRenderer=html_jscode, autoHeight=True, width=700) # , cellStyle=cellstyle_jscode , , cellStyle={"resizable": True,"autoHeight": True,"wrapText": True}
                    gb.configure_side_bar()
                    gb.configure_selection("single")
                    gridOptions = gb.build()
                    ag_resp = AgGrid(
                            df, 
                            data_return_mode=return_mode_value, 
                            update_mode=update_mode_value,
                            fit_columns_on_grid_load=True,                
                            gridOptions=gridOptions, 
                            allow_unsafe_jscode=True,
                            height=600,
                            enable_enterprise_modules=True
                            )#, enable_enterprise_modules=True
                    selected = ag_resp['selected_rows']
                    lexeme_count = df[(df.score > 0.2) & (df.lexeme !=word)].lexeme.value_counts().head(20)
                    # pie reprensentation
                    fig, ax = plt.subplots(figsize=(5, 5))
                    ax.pie(lexeme_count, labels=lexeme_count.index, wedgeprops = { 'linewidth' : 7, 'edgecolor' : 'white'})
                    #display a white circle in the middle of the pie chart
                    ax.set_title("20 most frequent similar contextual lexemes (Gallica)")
                    p = plt.gcf()
                    p.gca().add_artist(plt.Circle( (0,0), 0.7, color='white'))
                    st.pyplot(fig)

                with col4:
                    st.info("JSI data ("+ str(len(data2)) + " words for " + str(data2count) + " sentences)")

                    #st.info("The lexems below are the result of the fill-mask process applied to all sentences for the main lexem. Number of sentences for which they appear, and average score is given. By selecting a row, you will acess to the sentences and the score of the lexem.")
                    #st.markdown("**Word : " + word + ", Corpus : "+ corpus + ", Language model : " + embed_model + "**")
                    
                    # ag grid
                    ord_dict = [{"lexeme":tok.lower(), "score" : round(sent_score[1],5), "sentence": re.sub('<mask>', '<mark>'+word+'</mark>',sent_score[0])}  for tok in data2 for sent_score in data2[tok]]
                    df = pd.DataFrame(ord_dict)
                    # first datagrid
                    gb = GridOptionsBuilder.from_dataframe(df)
                    return_mode_value = DataReturnMode.__members__['FILTERED']
                    update_mode_value = GridUpdateMode.__members__['MODEL_CHANGED']            
                    gb.configure_pagination()
                    gb.configure_default_column(groupable=True, value=True, enableRowGroup=True, aggFunc='count', editable=False)
                    gb.configure_column('lexeme', rowGroup=True, sort="desc")
                    gb.configure_column('score', aggFunc="avg")
                    gb.configure_column("sentence", wrapText=True, flex=2, cellRenderer=html_jscode, autoHeight=True, width=700) # , cellStyle=cellstyle_jscode , , cellStyle={"resizable": True,"autoHeight": True,"wrapText": True}
                    gb.configure_side_bar()
                    gb.configure_selection("single")
                    gridOptions = gb.build()
                    ag_resp = AgGrid(
                            df, 
                            data_return_mode=return_mode_value, 
                            update_mode=update_mode_value,
                            fit_columns_on_grid_load=True,                
                            gridOptions=gridOptions, 
                            allow_unsafe_jscode=True,
                            height=600,
                            enable_enterprise_modules=True
                            )#, enable_enterprise_modules=True
                    selected = ag_resp['selected_rows']
                    # pie reprensentation
                    lexeme_count2 = df[(df.score > 0.2) & (df.lexeme !=word)].lexeme.value_counts().head(20)
                    fig, ax = plt.subplots(figsize=(5, 5))
                    ax.pie(lexeme_count2, labels=lexeme_count2.index, wedgeprops = { 'linewidth' : 7, 'edgecolor' : 'white'})
                    #display a white circle in the middle of the pie chart
                    ax.set_title("20 most frequent similar contextual lexemes (JSI)")
                    p = plt.gcf()
                    p.gca().add_artist(plt.Circle( (0,0), 0.7, color='white'))
                    st.pyplot(fig)

        else:
            ## word embeddings
            with st.expander("Word embeddings"):
                st.info("The lexems below are the result of the word embeddings with Fasttext, either the pretrained model for the recent period, either a trained model on a Gallica Press corpous (1850-1930)")

                word_embs = pickle.load(open("./input_files/fasttext.cc.fr.300.bin.evolsem_words.pkl", mode="rb"))
                word_embs2 = pickle.load(open("./input_files/fasttext.fasttext.gallica_corpus.cbow.bin.evolsem_words.pkl", mode="rb"))
                col3,col4 = st.columns(2)
                with col3 :
                    st.subheader("1850-1930")
                    if word in word_embs2:
                        df1 = pd.DataFrame(word_embs2[word], columns=['score','word']).reset_index(drop=True)
                        st.dataframe(df1, width=300)
                        #st.json(word_embs2[word])
                    else:
                        st.write("No word embeddings for this word")
                with col4:
                    st.subheader("2000-2020")
                    if word in word_embs:
                        df = pd.DataFrame(word_embs[word], columns=['score','word']).reset_index(drop=True)
                        st.dataframe(df, width=300)
                        #st.json(word_embs[word])
                    else:
                        st.write("No word embeddings for this word")

            # Contextual embeddings
            data = pickle.load(open("input_files/"+corpus+"."+word+ ".csv."+embed_model+ ".fill_mask.pkl",mode="rb"))
            #print(data)
            with st.expander("Contextual embeddings"):
                st.info("The lexems below are the result of the fill-mask process applied to all sentences for the main lexem. Number of sentences for which they appear, and average score is given. By selecting a row, you will acess to the sentences and the score of the lexem.")
                st.markdown("**Word : " + word + ", Corpus : "+ corpus + ", Language model : " + embed_model + "**")
                
                # ag grid
                ord_dict = [{"lexeme":tok, "score" : round(sent_score[1],5), "sentence": re.sub('<mask>', '<mark>'+word+'</mark>',sent_score[0])}  for tok in data for sent_score in data[tok]]
                df = pd.DataFrame(ord_dict)
                # first datagrid
                gb = GridOptionsBuilder.from_dataframe(df)
                return_mode_value = DataReturnMode.__members__['FILTERED']
                update_mode_value = GridUpdateMode.__members__['MODEL_CHANGED']            
                gb.configure_pagination()
                gb.configure_default_column(groupable=True, value=True, enableRowGroup=True, aggFunc='count', editable=False)
                gb.configure_column('lexeme', rowGroup=True, sort="desc")
                gb.configure_column('score', aggFunc="avg")
                gb.configure_column("sentence", wrapText=True, flex=2, cellRenderer=html_jscode, autoHeight=True, width=700) # , cellStyle=cellstyle_jscode , , cellStyle={"resizable": True,"autoHeight": True,"wrapText": True}
                gb.configure_side_bar()
                gb.configure_selection("single")
                gridOptions = gb.build()
                ag_resp = AgGrid(
                        df, 
                        data_return_mode=return_mode_value, 
                        update_mode=update_mode_value,
                        fit_columns_on_grid_load=True,                
                        gridOptions=gridOptions, 
                        allow_unsafe_jscode=True,
                        height=600,
                        enable_enterprise_modules=True
                        )#, enable_enterprise_modules=True
                selected = ag_resp['selected_rows']
