# Scripts to retrieve polysemous words from French Wiktionary

This directory contains python scripts to extract polysemous words (n, v, adj) from GLAWI (http://redac.univ-tlse2.fr/lexiques/glawi.html) XML version of French Wiktionary (2015) and store word, part of speech and definitions into a mysql database for EvolSem web interface (https://tal.lipn.univ-paris13.fr/neoveille/html/evolsem2/html/index.php).

# Procedures

## 1. Download GLAWI
You first have to download GLAWI from http://redac.univ-tlse2.fr/lexiques/glawi.html into this directory and untar it.

## 2 Retrieve data from GLAWI
Then you can edit `1.extractWiktionnaire_n_v_adj_def_usage_examples.py` to choose the part of speech you want to extract. Then execute the script (python3). It generates three files:

- `wiktionnary_ + part_of_speech + _def.tsv` : tabular format, one word-part_of_speech-sense_number-definition-examples per line. This file can be deleted after the two other files are generated.
- `liste_words_def.txt`: tabular format, merging word-part_of_speech-senses-examples on each line.
- `liste_words_def_light.txt`: tabular format, the same as above but without examples. This is the prefered file from which data is stored into the database.


## 3. Store data into Mysql DB
The last step consists in storing lexemes into wiktionary_lexicon table (evolsem )mysql db, see mysql subdirectory for db structure and sql creation scripts). The python script `2.save_wiktionary_data_to_db.py` can be tuned to execute all or specific tasks.

The default tasks (`all`) are : retrieve for each word (in `liste_words_def_light.txt`) its frequency into europaena_news (1800-1940 corpus, corpus 1) and rss_french (2016-2022, corpus 2) Solr corpora, save these frequencies into files (`europaena_news.word_counts.csv` and `rss_french_word_counts.csv`), then populate the wiktionary_lexicon table with : language, word, part_of_speech, frequency in corpus 1, frequency in corpus 2 and definitions. Then you can browse and edit the data into EvolSem web interface.


The next step : to retrieve sentences for these words, parse these sentences and store them into evolsem db, please go to `collect_data` subdirectory for details.



