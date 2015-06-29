#!/usr/bin/env python
from sklearn.feature_extraction import DictVectorizer
import nltk
import math

from config import es as default_es

ENGLISH_STOPWORDS = set(nltk.corpus.stopwords.words('english'))

def tfidf(tf, df, n_doc):
    idf = math.log(n_doc / float(df))
    return tf * idf

def terms_from_es_json(doc, rm_stopwords=True, pos_tags=[]):
    terms = {}
    docterms = doc["term_vectors"]["text"]["terms"]
    n_doc = doc["term_vectors"]["text"]["field_statistics"]["doc_count"]
    valid_words = docterms.keys()
    if rm_stopwords:
        no_stopwords = [k for k in docterms.keys() if k not in ENGLISH_STOPWORDS and (len(k) > 2)]
        valid_words = no_stopwords

    if len(pos_tags) > 0:
        tagged = nltk.pos_tag(docterms)
        #tags = ['NN', 'NNS', 'NNP', 'NNPS', 'VBN', 'JJ']
        valid_words = [tag[0] for tag in tagged if tag[1] in tags]

    for k in valid_words:
        try:
            if docterms[k]["ttf"] > 1:
                terms[k] = {'tfidf':tfidf(docterms[k]["term_freq"], docterms[k]["doc_freq"], n_doc),
                            'tf': docterms[k]["term_freq"],
                            'ttf': docterms[k]["ttf"],
                        }
        except KeyError:
            print k, " ", docterms[k]

    return terms

def getTermStatistics(all_hits, es_index='memex', es_doc_type='page', es=None):
    if es is None:
        es = default_es

    stats = []
    docs = []

    ttf = {}
    for i in range(0, len(all_hits), 10):
        hits = all_hits[i:i+10]

        term_res = es.mtermvectors(index=es_index,
                                   doc_type=es_doc_type,
                                   term_statistics=True, 
                                   fields=['text'], 
                                   ids=hits)

        for doc in term_res['docs']:
            if doc.get('term_vectors'):
                if 'text' in doc['term_vectors']:
                    docs.append(doc['_id'])
                    res = terms_from_es_json(doc)
                    stats.append(res)
                    for k in res.keys():
                        ttf[k] = res[k]['ttf']
    
    tfidfs = []
    for stat in stats:
        tfidf={}
        for k in stat.keys():
            tfidf[k] =stat[k]['tfidf']
        tfidfs.append(tfidf)

    tfs = []
    for stat in stats:
        tf={}
        for k in stat.keys():
            tf[k] =stat[k]['tf']
        tfs.append(tf)
    
    v_tfidf = DictVectorizer()
    v_tf = DictVectorizer()

    result = [v_tfidf.fit_transform(tfidfs), v_tf.fit_transform(tfs), ttf, v_tfidf.get_feature_names(), docs]

    return result

