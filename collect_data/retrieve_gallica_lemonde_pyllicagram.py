# https://github.com/regicid/pyllicagram
import pandas as pd
from pyllicagram import pyllicagram
import os
from urllib.parse import quote
import plotly.express as px


def load_frequency_data(words, c, debut, fin, resolution):
    foutall = outputdir + c + '.' + headword + '.csv'
    if os.path.exists(foutall):
        return pd.read_csv(foutall)
    else:
        list_dfs=[]
        for w in words:
            print("parsing : ", w, c, debut, fin, resolution)
            outfile = outputdir + c + '.' + w + '.csv'
            if os.path.isfile(outfile):
                df = pd.read_csv(outfile)
                if 'word' not in df.columns:
                    df['word']=w
            else:
                # here is the main function
                df = pyllicagram(recherche=quote(w), corpus=c, debut=debut, fin=fin, resolution=resolution)
                df['word']=w
                df.to_csv(outfile, index=False)
            list_dfs.append(df)
        dfall= pd.concat(list_dfs)
        dfall.to_csv(foutall, index=False)
        return dfall

def plot_data(df, resolution, corpus, headword):
    df['ratio'] = df['ratio']*1000000
    fig = px.line(df, x=resolution, y="ratio", color='word')
    fig.update_layout(title_text='Evolution of relative frequency in corpus [' + corpus + '] for word family [' + headword.split('_')[0] + ']', title_x=0.5)
    fig.update_yaxes(title_text='relative frequency per million')
    fig.update_xaxes(title_text='Year')
    fig.update_layout(
            #labels=dict(ratio="relative frequency per 100000"),
            yaxis=dict(
                #tickmode='linear',
                #label="relative frequency per 100000",
                tickformat=".2f",
                #tick0=0.0,
                #dtick=100
            )
        )
    fig.show()    
######## main
headword= 'téléphone_wordfamily'
words = ['téléphone', 'smartphone', 'smart phone', 'téléphone mobile', 'téléphone portable', 'téléphone cellulaire', 'téléphone intelligent', 'ordiphone']
outputdir= './pyllicagram/'




headword= 'couleur_wordfamily'
words = ['noir', 'rouge','vert','bleu','blanc']
outputdir= './pyllicagram/'
os.makedirs(outputdir, exist_ok=True)
corpus= ['lemonde','presse','livres'] # or presse or livres

for c in corpus:
    if c=='lemonde':
        debut =1944
        fin=2022
        resolution='annee'
    else:
        debut =1800
        fin=1950
        resolution='annee'
    df = load_frequency_data(words, c, debut, fin, resolution)
    print(df.info())
    #if resolution == 'mois':
    #    df['annee-mois']= str(df['annee']) + '-' + str(df['mois'])
    #    resolution = 'annee-mois'
    resolution='annee'
    plot_data(df, resolution, c, headword)
# combine presse + lemonde
#foutall1 = outputdir + 'lemonde.' + headword + '.csv'
#foutall2 = outputdir + 'presse.' + headword + '.csv'
#df1 = pd.read_csv(foutall1)
#df2 = pd.read_csv(foutall2)
#df2 = df2[df2.annee < 1944]
#df = pd.concat([df1, df2])
#plot_data(df, resolution, 'Presse + Le Monde', headword)


