import streamlit as st
#import plotly.figure_factory as ff
#import plotly.express as px
#import plotly.graph_objects as go
import pandas as pd
from glob import glob
import re, sys
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
if analysis == 'Specific Sentence Analysis2':
    
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
    #print(len(wordlistboth))
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
            st.subheader("Sorry, not yet implemented. Come back later....")
            doc1 = udapi.Document("input_files/gallica." +word+".csv.udpipe.conllu")
            doc2 = udapi.Document("input_files/jsi." +word+".csv.udpipe.conllu")
        else:
            doc = udapi.Document(wordsdic[word])
            # global variables
            id_sentences={}
            global_pos={}
            global_dep={}
            lemma_pats={}
            pos_pats={}
            internal_glob_pattern=[]
            st.subheader("Dependency trees loaded : " + str(doc._highest_bundle_id) + " sentences")

            # bootstrap nav menu
            #st.markdown('''<ul class="nav nav-tabs" id="myTab" role="tablist"><li class="nav-item"><a class="nav-link active" id="home-tab" data-toggle="tab" href="#internal_dep" role="tab" aria-controls="internal_dep" aria-selected="true">Internal Dependencies</a></li><li class="nav-item"><a class="nav-link" id="external-tab" data-toggle="tab" href="#external_dep" role="tab" aria-controls="external_dep" aria-selected="false">External Dependencies</a></li><li class="nav-item"><a class="nav-link" id="comparedep-tab" data-toggle="tab" href="#comparedep" role="tab" aria-controls="comparedep" aria-selected="false">Compare Dependencies</a></li></ul><div class="tab-content" id="myTabContent">''',unsafe_allow_html=True)
            for bundle in doc.bundles:
                #print(bundle.bundle_id)
                tree = bundle.get_tree()
                #print(len(tree))
                sent_id = bundle.bundle_id
                id_sentences[sent_id]=tree.compute_text()
                for node in tree.descendants:
                    if node.form.lower() == word:
                        pos = node.upos
                        global_pos[pos] = global_pos.get(pos,0) + 1
                        dep = node.deprel
                        udep = node.udeprel
                        #node.misc['mark']='Mark'
                        # pos and lemma patterns (internal structure)
                        internal_pos_pattern = udpipe_utils.compute_internal_pattern(node,word,sent_id)
                        if internal_pos_pattern:
                            internal_glob_pattern.append(internal_pos_pattern)
                        #pos_pattern = udpipe_utils.compute_text_feature(node,word,  feature="upos")
                        #if pos_pattern:
                        #    pos_pats[pos_pattern] = pos_pats.get(pos_pattern,0)+1
                        #lemma_pattern = udpipe_utils.compute_text_feature(node,word,  feature="lemma")
                        #if lemma_pattern:
                        #    lemma_pats[lemma_pattern] = lemma_pats.get(lemma_pattern,0)+1
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
            
            with st.expander("Linear structure analysis (to be done)"):
                st.info("This section presents the most frequent linear structure around the focus word (limited to 3 token left and right).")

            with st.expander("Internal Dependency Structure"):
                st.info("This section presents the internal structure of Nouns and Verbs derived from dependency analysis (UDPipe). For Nouns, Noun + ADJ, ADJ + NOUN, NOUN PREP NOUN, NOUN + PROPREL and other internal structures are proposed. For Verbs, internal flexional structure is proposed, as well as auxiliary and modal structures.")
                st.write(global_pos)

                df_depint = pd.DataFrame(internal_glob_pattern)
                print(df_depint.info())
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
    #print(files) 
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
        if re.search('\+',corpus):
            st.subheader("Sorry, not yet implemented. Come back later....")
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

    #            with col2:
    #                count_data = []
    #                median_data = []
    #                for elt in ord_dict:
    #                    count_data.append(elt['count'])
    #                    median_data.append(elt['median'])
    #                fig1 = px.violin(count_data, orientation="h",height=200)
                    # hide subplot y-axis titles and x-axis titles
    #                for axis in fig1.layout:
    #                    if type(fig1.layout[axis]) == go.layout.YAxis:
    #                        fig1.layout[axis].title.text = ''
    #                    if type(fig1.layout[axis]) == go.layout.XAxis:
    #                        fig1.layout[axis].title.text = ""
    #                fig1.update_layout(title={'text': "Number of sentences Distribution",
    #                                        'y':0.9,
    #                                        'x':0.5,
    #                                        'xanchor': 'center',
    #                                        'yanchor': 'top'})
    #                fig2 = px.violin(median_data, orientation="h",height=200)              
    #                for axis in fig2.layout:
    #                    if type(fig2.layout[axis]) == go.layout.YAxis:
    #                        fig2.layout[axis].title.text = ''
    #                    if type(fig2.layout[axis]) == go.layout.XAxis:
    #                        fig2.layout[axis].title.text = ""
    #                fig2.update_layout(title={'text': "Mean Score Distribution",
    #                                        'y':0.9,
    #                                        'x':0.5,
    #                                        'xanchor': 'center',
    #                                        'yanchor': 'top'})
                    # scatter plot
    #                df_g = pd.DataFrame(ord_dict)
    #                fig3 = px.scatter(df_g, x="count", y="median", hover_name="lexem",height=200)
    #                for axis in fig3.layout:
    #                    if type(fig3.layout[axis]) == go.layout.YAxis:
    #                        fig3.layout[axis].title.text = 'Mean Score'
    #                    if type(fig3.layout[axis]) == go.layout.XAxis:
    #                        fig3.layout[axis].title.text = "Number of sentences"
    #                fig3.update_layout(title={'text': "Correlation (Number of sentences / Mean score)",
    #                                            'y':0.9,
    #                                            'x':0.5,
    #                                            'xanchor': 'center',
    #                                            'yanchor': 'top'})
    #                st.plotly_chart(fig1, use_container_width=True,config = {"displayModeBar": False},)
    #                st.plotly_chart(fig2, use_container_width=True,config = {"displayModeBar": False})
    #                st.plotly_chart(fig3, use_container_width=True,config = {"displayModeBar": False})
    #            if len(selected)==1:
                    #st.subheader(selected[0]['lexem'])
    #                dico_sel = [{'score':round(d[1],5),'sentence': re.sub('<mask>', '<mark>'+word+'</mark>',d[0])} for d in data[selected[0]['lexem']]]
    #                sel_scores = [round(d[1],5) for d in data[selected[0]['lexem']]]
    #                df_sel = pd.DataFrame(dico_sel)
    #                gb2 = GridOptionsBuilder.from_dataframe(df_sel)
    #                gb2.configure_pagination()
                    #gb2.configure_auto_height(autoHeight=True)
    #                gb2.configure_column('score', sort="desc", width="20%")
    #                gb2.configure_column("sentence", flex=2, cellRenderer=html_jscode, wrapText=True, autoHeight=True) # , cellStyle=cellstyle_jscode , , cellStyle={"resizable": True,"autoHeight": True,"wrapText": True}
    #                gridOptions2 = gb2.build()
    #                df_detail = AgGrid(df_sel,gridOptions=gridOptions2, allow_unsafe_jscode=True, fit_columns_on_grid_load=True, width="autoWidth")#
    #                chart_data = pd.DataFrame(sel_scores, columns=['lexeme'])

                    # Create distplot with custom bin_size
                    # And within an expander
    #               my_expander = st.expander("Histogramme", expanded=True)
    #               with my_expander:
                        #hist_data = [chart_data]
                        #group_labels = [selected[0]['lexem']] # name of the dataset
                        #fig = ff.create_distplot(hist_data, group_labels)

    #                  fig = px.histogram(chart_data, marginal="box")                
    #                  st.plotly_chart(fig, use_container_width=True)


