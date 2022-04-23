
from lxml import etree

tree = etree.parse("GLAWI_FR_work_D2015-12-26_R2016-05-18.xml")

words = {'cafetière':'N','déboire':'N','décéder':'V','disparaître':'V','renard':'N','trépasser':'V','veille':'N','oseille':'N','blé':'N','ressentiment':'N','abîmer':'V','addition':'N','bureau':'N','courrier':'N','déjeuner':'N','dîner':'N','langue':'N','réaliser':'V','louer':'V','emprunter':'V','cabinet':'N','bordel':'N','manières':'N'}

root = tree.getroot()
cat = 'adj' # change for nom, verbe as desired
fout = open("wiktionnary_" + cat + "_def.tsv", mode="w")
fout.write("word\tsense_number\tusage_note\tdefinition\texemples\n")

for pos in root.xpath("//article/text/pos"):
    if pos.get("type").find(cat) != -1 and pos.get("lemma").find("1") != -1 and len(pos.xpath("definitions/definition")) > 1:
        headword = (pos.find("../..")).find('title').text
        if headword.islower():
            print(headword)
            #etree.dump(pos)
            compteur=0
            for defi in pos.iter('definition'):
                marque_usage=[]
                exemples=[]
                compteur=compteur+1
                for gloss in defi.iter('gloss'):
                    def_text = gloss.find('txt').text
                    #print(def_text)
                for us in defi.iter('label'):
                    marque_usage.append(us.get('type') + ":" + us.get('value'))                

                for us in defi.iter('example'):
                    exemples.append(us.find('txt').text)  
                print(headword + "\t" + str(compteur) + "\t" + str(marque_usage) + "\t" + def_text + "\t" + str(exemples) )
                fout.write(str(headword) + "\t" + str(compteur) + "\t" + str(marque_usage) + "\t" + str(def_text) + "\t" + str(exemples) +"\n")

fout.close()



# adj
fout = open("liste_words_def.txt", mode='w')
fout2 = open("liste_words_def_light.txt", mode='w')
dfn = pd.read_csv('wiktionnary_adj_def.tsv', sep="\t")
dfn.fillna('', inplace=True)
#print(dfn.info)
#print(dfn.head())
nouns = dfn.word.unique().tolist()
for noun in nouns:
	res = ''
	res2 = ''
	data = dfn[dfn.word==noun].to_dict(orient='records')
	for elt in data:
		print(elt)
		res += str(elt['sense_number']) + '. ' + elt['usage_note'] + ' ' + elt['definition']+ ' ' + elt['exemples'] + '<br/>'
		res2 += str(elt['sense_number']) + '. ' + elt['usage_note'] + ' ' + elt['definition'] + '<br/>'
	fout.write(noun + "\tADJ\t" + res + "\n")
	fout2.write(noun + "\tADJ\t" + res2 + "\n")
	
exit()
