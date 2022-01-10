from typing import no_type_check_decorator
import udapi
from udapi.block.write.html import Html
import re, sys

global udeprel_def
udeprel_def = {
"conjonctive_relation":"Conjonction of elements of same pos",
"argumentative_structure":"Any core arguments structure",
"acl":"clausal modifier of noun (adnominal clause)",
"acl:relcl":"relative clause modifier",
"advcl":"adverbial clause modifier",
"advmod":"adverbial modifier",
"advmod:emph":"emphasizing word, intensifier",
"advmod:lmod":"locative adverbial modifier",
"amod":"adjectival modifier",
"appos":"appositional modifier",
"aux":"auxiliary",
"aux:pass":"passive auxiliary",
"case":"case marking",
"cc":"coordinating conjunction",
"cc:preconj":"preconjunct",
"ccomp":"clausal complement",
"clf":"classifier",
"compound":"compound",
"compound:lvc":"light verb construction",
"compound:prt":"phrasal verb particle",
"compound:redup":"reduplicated compounds",
"compound:svc":"serial verb compounds",
"conj":"conjunct",
"cop":"copula",
"csubj":"clausal subject",
"csubj:pass":"clausal passive subject",
"dep":"unspecified dependency",
"det":"determiner",
"det:numgov":"pronominal quantifier governing the case of the noun",
"det:nummod":"pronominal quantifier agreeing in case with the noun",
"det:poss":"possessive determiner",
"discourse":"discourse element",
"dislocated":"dislocated elements",
"expl":"expletive",
"expl:impers":"impersonal expletive",
"expl:pass":"reflexive pronoun used in reflexive passive",
"expl:pv":"reflexive clitic with an inherently reflexive verb",
"fixed":"fixed multiword expression",
"flat":"flat multiword expression",
"flat:foreign":"foreign words",
"flat:name":"names",
"goeswith":"goes with",
"iobj":"indirect object",
"list":"list",
"mark":"marker",
"nmod":"nominal modifier",
"nmod:poss":"possessive nominal modifier",
"nmod:tmod":"temporal modifier",
"nsubj":"nominal subject",
"nsubj:pass":"passive nominal subject",
"nummod":"numeric modifier",
"nummod:gov":"numeric modifier governing the case of the noun",
"obj":"object",
"obl":"oblique nominal",
"obl:agent":"agent modifier",
"obl:arg":"oblique argument",
"obl:lmod":"locative modifier",
"obl:tmod":"temporal modifier",
"orphan":"orphan",
"parataxis":"parataxis",
"punct":"punctuation",
"reparandum":"overridden disfluency",
"root":"root",
"vocative":"vocative",
"xcomp":"open clausal complement"}


pronouns = ['me',"m'","te","t'","se","s'","nous","vous"]

def compute_text_feat(doc, feature='form', use_mwt=True):
        """Return a string representing this subtree's linear representation according to feature (detokenized).

        Compute the string by concatenating given feature of nodes
        (words and multi-word tokens) and joining them with a single space,
        unless the node has SpaceAfter=No in its misc.
    
        Technical details:
        If called on root, the root's form (<ROOT>) is not included in the string.
        If called on non-root nodeA, nodeA's feature is included in the string,
        i.e. internally descendants(add_self=True) is used.
        Note that if the subtree is non-projective, the resulting string may be misleading.

        Args:
        doc: the document tree
        feature: the feature to use (form, upos, lemma but other node features can also be used)
        use_mwt: consider multi-word tokens? (default=True)
        """
        string = ''
        last_mwt_id = 0
        for node in doc.descendants(add_self=not doc.is_root()):
            mwt = node.multiword_token
            if use_mwt and mwt:
                if node._ord > last_mwt_id:
                    last_mwt_id = mwt.words[-1]._ord
                    string += eval('mwt.'+feature)
                    if mwt.misc['SpaceAfter'] != 'No':
                        string += ' '
            else:
                string += eval('node.'+feature)
                if node.misc['SpaceAfter'] != 'No':
                    string += ' '
        return string.rstrip()

def compute_children_text(root, use_mwt=True):
        """Return a string representing this subtree's (limited to children) text (detokenized).

        Compute the string by concatenating forms of nodes
        (words and multi-word tokens) and joining them with a single space,
        unless the node has SpaceAfter=No in its misc.

        Technical details:
        If called on root, the root's form (<ROOT>) is not included in the string.
        If called on non-root nodeA, nodeA's form is included in the string,
        i.e. internally children(add_self=True) is used.
        Note that if the subtree is non-projective, the resulting string may be misleading.

        Args:
        use_mwt: consider multi-word tokens? (default=True)
        """
        string = ''
        last_mwt_id = 0
        for node in root.children(add_self=not root.is_root()):
            mwt = node.multiword_token
            if use_mwt and mwt:
                if node._ord > last_mwt_id:
                    last_mwt_id = mwt.words[-1]._ord
                    string += mwt.form
                    if mwt.misc['SpaceAfter'] != 'No':
                        string += ' '
            else:
                string += node.form
                if node.misc['SpaceAfter'] != 'No':
                    string += ' '
        return string.rstrip()

def compute_text_feature(root, word, feature="upos"):
        """Return a string representing this subtree's (limited to children) text (detokenized).

        Compute the string by concatenating forms of nodes
        (words and multi-word tokens) and joining them with a single space,
        unless the node has SpaceAfter=No in its misc.

        Technical details:
        If called on root, the root's form (<ROOT>) is not included in the string.
        If called on non-root nodeA, nodeA's form is included in the string,
        i.e. internally children(add_self=True) is used.
        Note that if the subtree is non-projective, the resulting string may be misleading.

        Args:
        use_mwt: consider multi-word tokens? (default=True)
        """
       
        string = ''
        pos = root.upos
        if pos == "NOUN":
            for node in root.descendants(preceding_only=True, add_self=True):
                if node.form==word:
                    string += node.form
                elif node.upos in ("ADJ","NOUN"):
                    string += eval("node."+feature)
                string += ' '
            for node in root.descendants(following_only=True):
                if node.upos not in ("PUNCT"):
                    string += eval("node."+feature)
                    string += ' '
            return string.strip()
        elif pos =="VERB":
            return compute_text_feature_bk(root, word, feature)
        

def compute_text_feature_bk(root, word, pos, feature="upos", conditions='node.upos !="DET"', use_mwt=False):
        """Return a string representing this subtree's (limited to children) text (detokenized).

        Compute the string by concatenating forms of nodes
        (words and multi-word tokens) and joining them with a single space,
        unless the node has SpaceAfter=No in its misc.

        Technical details:
        If called on root, the root's form (<ROOT>) is not included in the string.
        If called on non-root nodeA, nodeA's form is included in the string,
        i.e. internally children(add_self=True) is used.
        Note that if the subtree is non-projective, the resulting string may be misleading.

        Args:
        use_mwt: consider multi-word tokens? (default=True)
        """
        string = ''
        last_mwt_id = 0
        for node in root.descendants(add_self=not root.is_root()):
            mwt = node.multiword_token
            if use_mwt and mwt:
                if node._ord > last_mwt_id:
                    last_mwt_id = mwt.words[-1]._ord
                    string += eval("mwt."+feature)
                    if mwt.misc['SpaceAfter'] != 'No':
                        string += ' '
            else:
                if node.form.lower()==word:
                    string += node.form
                else:
                    string += eval("node."+feature)
                string += ' '
        return string.rstrip()



def compute_internal_pattern(root,word, sent_id):
        '''Compute internal morphosyntactical patterns for Noun and Verbs'''
        strform = ''
        strlemma=''
        strpos=''
        pos = root.upos
        node_id = root.ord
        if pos == "NOUN":
            for node in root.descendants(preceding_only=True, add_self=True):
                if node.form==word:
                    strform += node.form + ' '
                    strlemma += node.form + ' '
                    strpos += node.form + ' '
                elif node.upos in ("ADJ","NOUN"):
                    strform += node.form + ' '
                    strlemma += node.lemma + ' '
                    strpos += node.upos + ' '
            for node in root.descendants(following_only=True):
                if node.upos not in ("PUNCT"):
                    strform += node.form + ' '
                    strlemma += node.lemma + ' '
                    strpos += node.upos + ' '
            return {'id_sent':sent_id, 'form':strform.strip(),'lemma':strlemma.strip(), 'pos':strpos.strip()}
        elif pos =="VERB":
            for node in root.children(add_self=not root.is_root()):
                if node.form.lower()==word:
                    strform += node.form + ' '
                    strlemma += node.lemma + ' '
                    strpos += node.lemma + ' '
                elif node.upos in ("AUX") and node.udeprel=="aux" and node.ord > node_id-4 :
                    strform += node.form + ' '
                    strlemma += node.lemma + ' '
                    strpos += node.upos + ' '
                    if node.next_node.upos=="ADP":
                        strform += node.next_node.form + ' '
                        strlemma += node.next_node.lemma + ' '
                        strpos += node.next_node.upos + ' '

                elif  node.upos=="PRON" and node.form in pronouns and node.udeprel in ("obj",'iobj') and node.ord==node_id-1:
                    strform += node.form + ' '
                    strlemma += "se" + ' '
                    strpos += node.upos + ' '
            return {'id_sent':sent_id, 'form':strform.strip(),'lemma':strlemma.strip(), 'pos':strpos.strip()}
     

def retrieve_external_pattern(node,sent_id):
    ''' Retrieve dependency pattern depending on on dependency relation on node'''
    pos = node.upos
    dep = node.deprel
    udep = node.udeprel
    node.misc['mark']='Mark'
    # get core agurments and non core dependents (NOUN and VERB)
    if pos=="NOUN":
        # verb + NOUN
        if udep in ('obj','nsubj','iobj'):
            return {'id_sent':sent_id,'lemma':node.parent.lemma, 'form':node.parent.form,"pos":node.parent.upos}
            
        # VERB + PREP + POS / NOUN PREP NOUN
        elif udep in('obl','nmod'):# x s'est dit heureux de l'addition et affaire d'adition / résultat d'une addition:  parent + preceding.deprel==case
            resform = node.parent.form
            reslemma = node.parent.lemma
            respos = node.parent.upos
            for node2 in node.children(preceding_only=True):
                resform = resform + " " + node2.form
                reslemma = reslemma + " " + node2.lemma
                respos = respos + " " + node2.upos
            return {'id_sent':sent_id, 'form':resform, 'lemma':reslemma, 'pos':respos}
        # else
        #elif udep in ('flat','fixed','compound'):
        #    node.draw(mark="mark")
        #if udep in ('parataxis','ccomp','xcomp','appos'):
        #    node.root.draw(mark="mark")

        else:
            if node.is_root():
                np = node.compute_text()
            else:
                np = node.parent.compute_text()
            return {'id_sent':sent_id, 'form':np}
            
def retrieve_external_pattern2(node,sent):
    ''' Retrieve dependency pattern depending on on dependency relation on node'''
    pos = node.upos
    # get core agurments and non core dependents (NOUN and VERB)
    if pos in ("NOUN",'PROPN'):
        return retrieve_external_patterns_noun(node,sent)
    elif pos== "VERB":
        return retrieve_external_patterns_verb(node,sent)

def retrieve_external_patterns_noun(node,sent):
        '''Specific pattern discovery for French nouns : nsubj, obj, iobj, obl, nmod, appos, acl'''
        # verb + NOUN
        if node.udeprel in ('obj','nsubj','iobj','amod','xcomp','ccomp','csubj'):
            if node.parent.upos in ("VERB","ADJ"):
                return {'id_sent':sent,'lemma':node.parent.lemma, 'form':node.parent.form,"pos":node.parent.upos}
            
        # VERB + PREP + POS / NOUN PREP NOUN
        elif node.udeprel in('obl','nmod'):# x s'est dit heureux de l'addition et affaire d'adition / résultat d'une addition:  parent + preceding.deprel==case
            if node.parent.upos in ("NOUN","ADJ",'VERB'):
                resform = node.parent.form
                reslemma = node.parent.lemma
                respos = node.parent.upos
                for node2 in node.children(preceding_only=True):
                    resform = resform + " " + node2.form
                    if node2.upos == "DET":
                        reslemma = reslemma + " " + node2.upos
                    else:
                        reslemma = reslemma + " " + node2.lemma

                    respos = respos + " " + node2.upos
                return {'id_sent':sent, 'form':resform, 'lemma':reslemma, 'pos':respos}
        elif node.udeprel in('conj'):# x s'est dit heureux de l'addition et affaire d'adition / résultat d'une addition:  parent + preceding.deprel==case
            if node.parent.upos in ("NOUN"):
                resform = node.parent.form
                reslemma = node.parent.lemma
                respos = node.parent.upos
                for node2 in node.parent.children:
                    if node2.upos in ("NOUN") and node2.udeprel =="conj":
                        resform = resform + " CONJ " + node2.form
                        reslemma = reslemma + " CONJ " + node2.lemma
                        respos = respos + " CONJ " + node2.upos
                return {'id_sent':sent, 'form':resform, 'lemma':reslemma, 'pos':respos}

        elif node.udeprel in('appos'):# x s'est dit heureux de l'addition et affaire d'adition / résultat d'une addition:  parent + preceding.deprel==case
            if node.parent.upos in ("NOUN"):
                resform = node.parent.form
                reslemma = node.parent.lemma
                respos = node.parent.upos
                for node2 in node.children:
                    if node2.upos in ("NOUN") and node2.udeprel =="conj":
                        resform = resform + " APPOS " + node2.form
                        reslemma = reslemma + " APPOS " + node2.lemma
                        respos = respos + " APPOS " + node2.upos
                return {'id_sent':sent, 'form':resform, 'lemma':reslemma, 'pos':respos}


        else:
            if node.is_root():
                np = node.compute_text()
            else:
                np = node.parent.compute_text()
            return {'id_sent':sent, 'form':np,'lemma':np, 'pos':node.upos}


def retrieve_definitions(root,word):
    '''Function to retrieve definitory patterns'''


def retrieve_external_patterns_verb(node, sent):
        '''Specific pattern discovery for French verbs : core arguments, peripheral arguments, conjonctive constructions, copulative constructions'''
        resform = ''
        reslemma = ""
        respos = ""
        resdep = ""
        for node2 in node.children(preceding_only=True):
            if node2.udeprel in ('nsubj','obj','iobj','csubj','ccomp','xcomp','obl'):#'advcl','advmod'  or node2.upos=='VERB'
                if node2.upos in ("PRON","PROPN"):
                    resform = resform + " " + node2.form
                    reslemma = reslemma + " " + node2.upos
                    respos = respos + " " + node2.upos
                    resdep = resdep + " " + node2.udeprel
                else:
                    resform = resform + " " + node2.form
                    reslemma = reslemma + " " + node2.lemma
                    respos = respos + " " + node2.upos
                    resdep = resdep + " " + node2.udeprel
        resform = resform + " " +node.form
        reslemma = reslemma + " " +node.lemma
        respos = respos + " " +node.lemma
        resdep = resdep + " " + node.lemma

        for node2 in node.children(following_only=True):
            if node2.udeprel in ('nsubj','obj','iobj','csubj','ccomp','xcomp'): 
                if node2.upos in ('PROPN'):
                    resform = resform + " " + node2.form
                    reslemma = reslemma + " " + node2.upos
                    respos = respos + " " + node2.upos
                    resdep = resdep + " " + node2.udeprel                    
                else:
                    resform = resform + " " + node2.form
                    reslemma = reslemma + " " + node2.lemma
                    respos = respos + " " + node2.upos
                    resdep = resdep + " " + node2.udeprel                    
            # get case ADP as node3.children (preceding) +  node3
            elif node2.udeprel in ('obl'):
                for node3 in node2.children(preceding_only=True):
                    if node3.upos in ('DET','PROPN'): 
                        resform = resform + " " + node3.form
                        reslemma = reslemma + " " + node3.upos
                        respos = respos + " " + node3.upos
                        resdep = resdep + " " + node3.udeprel                    
                    else: 
                        resform = resform + " " + node3.form
                        reslemma = reslemma + " " + node3.lemma
                        respos = respos + " " + node3.upos
                        resdep = resdep + " " + node3.udeprel                    
                if node2.upos in ('DET','PROPN'): 
                    resform = resform + " " + node2.form
                    reslemma = reslemma + " " + node2.upos
                    respos = respos + " " + node2.upos
                    resdep = resdep + " " + node2.udeprel                    
                else: 
                    resform = resform + " " + node2.form
                    reslemma = reslemma + " " + node2.lemma
                    respos = respos + " " + node2.upos
                    resdep = resdep + " " + node2.udeprel                    
            # conjonction of verbs VERB CONJ VERB
            # get case ADP as node3.children (preceding) +  node3
            elif node2.udeprel in ('acl'):
                for node3 in node2.children(preceding_only=True):
                    if node3.udeprel in ('mark'): 
                        resform = resform + " " + node3.form
                        reslemma = reslemma + " " + node3.lemma
                        respos = respos + " " + node3.upos
                        resdep = resdep + " " + node3.udeprel                    
                resform = resform + " " + node2.form
                reslemma = reslemma + " " + node2.lemma
                respos = respos + " " + node2.upos
                resdep = resdep + " " + node2.udeprel                    

                        
        return {'id_sent':sent, 'form':resform, 'lemma':reslemma, 'pos':respos, 'dep_rel': resdep}



def retrieve_external_patterns_verb_conjrel(node, sent):
        '''Specific pattern discovery for French verbs : conjonctive relations'''
        resform = ''
        reslemma = ""
        respos = ""

        for node2 in node.children(following_only=True):
            # conjonction of verbs VERB CONJ VERB
            if node2.upos=='VERB' and node2.udeprel =="conj": 
                if resform == '':
                    resform = node.form + " CONJ " + node2.form
                    reslemma = node.lemma + " CONJ " + node2.lemma
                    respos = node.lemma + " CONJ " + node2.upos
                else:
                    resform = resform + " CONJ " + node2.form
                    reslemma = reslemma + " CONJ " + node2.lemma
                    respos = respos + " CONJ " + node2.upos
        if resform=='':
            return False
        else:
            return {'id_sent':sent, 'form':resform, 'lemma':reslemma, 'pos':respos}
