# -*- coding: utf-8 -*-
"""Regex_capture.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1GQXcZzbG5pBpdfshvVf0JiLef9BwHc_5
"""

# from google.colab import drive
# drive.mount('/content/drive')

!pip install segtok
!pip install pysbd
!git clone https://github.com/jsavelka/luima_sbd.git
!pip install -r /content/luima_sbd/requirements.txt

import re
import multiprocessing
from multiprocessing import Pool
from datetime import datetime
import json
from luima_sbd import sbd_utils
from bs4 import BeautifulSoup
import itertools
import requests
import json
import xml
import spacy
sp = spacy.load('en_core_web_sm')

#API requests
def api_call(name):
  API_KEY = "4d969d15b4c1362411a787ca1ebd0d1b0da5e31c"

  response = requests.get(
      'https://api.case.law//v1/cases/?full_case=false&name_abbreviation=' + name,
    # 'https://api.case.law/v1/cases/?court=us&page_size=5000',
    #'https://api.case.law/v1/courts/',
       headers={'Authorization': f'Token {API_KEY}', 'body_format':'json'},
    )
  data = response.json()
  return data

def containment_metric(doc1, doc2):
  doc1 = re.sub('[^A-Za-z0-9\s]+', '', doc1)
  doc2 = re.sub('[^A-Za-z0-9\s]+', '', doc2)

  words_doc1 = set(doc1.lower().split()) 
  words_doc2 = set(doc2.lower().split())

  intersection = words_doc1.intersection(words_doc2)

  min_len = min(len(words_doc1), len(words_doc2))

  return float(len(intersection))/ min_len

def Jaccard_Similarity(doc1, doc2): 
    
    # List the unique words in a document
    words_doc1 = set(doc1.lower().split()) 
    words_doc2 = set(doc2.lower().split())
    
    # Find the intersection of words list of doc1 & doc2
    intersection = words_doc1.intersection(words_doc2)

    # Find the union of words list of doc1 & doc2
    union = words_doc1.union(words_doc2)
        
    # Calculate Jaccard similarity score 
    # using length of intersection set divided by length of union set
    return float(len(intersection)) / len(union)

def return_title(name_abb):
  name_abb = re.sub(r"https:\/\/cite\.case\.law\/pdf\/\d+\/","", name_abb)
  name_abb = re.sub(r"%20", " ", name_abb)
  name_abb = re.sub(r".pdf", "", name_abb)
  return name_abb

def similarity_index(doc1, doc2):
  J = Jaccard_Similarity(doc1, doc2)
  C = containment_metric(doc1, doc2)
  S = (2*J*C)/(J+C)
  return S

# returns complete sentences where the sentence is being cited
def return_sent(json_file, link):
  soup2 = json_file["casebody"]["dataCleaned"]
  text2 = sbd_utils.text2sentences(str(soup2))

  titles = []
  for sent in text2:
    if link.text in sent:
      strimg = sent
  return strimg

def check_multi(soup):
  bool_1 = False
  lis = []
  for link in soup.find_all('extracted-citation'):
    para = link.get_text()
    check = True if para.find("§")!=-1 else False
    if link.has_attr('case-ids')==True and check==False:
    #print(str(link))
      ez = str(link.attrs['case-ids'])
      check2 = True if ez.find(",")!=-1 else False
      if check==False and check2==True:
        lis.append(ez)
        bool_1 = True
  return bool_1, lis

def multiple_links(json_file):
  new_list = {}
  link_dict = {}
  final_dict = {}
  soup = BeautifulSoup(json_file["casebody"]["data"], "xml")
  for link in soup.find_all('extracted-citation'):
    para = link.get_text()
    check = True if para.find("§")!=-1 else False
    if link.has_attr('case-ids')==True and check==False:
    #print(str(link))
      ez = str(link.attrs['case-ids'])
      check2 = True if ez.find(",")!=-1 else False
      if check==False and check2==True:
        #new_list[link] = return_sent(json_file, link)
        link_dict[str(link.attrs['case-ids'])] = return_sent(json_file, link)
        #final_dict[str(link)] = link
        
  return link_dict

def citation_graph_fn(file):
  start= file['casebody']['data'].find('<opinion')
  close= file['casebody']['data'].find('</casebody')
  opinion=file['casebody']['data'][start:close]
  id = file['id']
  print(id)
  soup = BeautifulSoup(opinion, 'lxml')
  for i in soup('blockquote'):
    i.decompose()
  for i in soup('page-number'):
    i.decompose()
  for i in soup('footnotemark'):
    i.decompose()   
  for i in soup('author'):
    i.decompose()  
  for i in soup('footnote'):
    i.decompose() 

  em_headers = soup.find_all("em")
  soup = str(soup)
  for head in em_headers:
    head2 = ".. " + str(head)
    soup = soup.replace(str(head), head2)

  soup2 = BeautifulSoup(soup, 'xml')

  match = []
  match2 = []
  text_match = {}
  text_match2= {}
  text2 = sbd_utils.text2sentences(soup2.text)
  for text in text2:
    beet = re.findall(r"([A-Za-z-’,.\s]+(\s?v\.\s?)+[A-Za-z-’,.\s()]+)", text)
    if beet:
      temp = list(list(zip(*beet))[0])
      text_match[temp[0]] = text

  for text in text2:
    beet2 = re.findall(r"(In\sre+[A-Za-z-’,.\s()&]+(Inc\.)?)", text)
    if beet2:
      temp2 = list(list(zip(*beet2))[0])
      text_match[temp2[0]] = text

  combinedfinal = {}
  for ele in text_match.keys():
    wordlist = []
    res = re.sub(r'[^\w\s]', '', ele.strip())
    sen = sp(res)
    for i, word in enumerate(sen):
      if str(word) == "v":
        try:
          wordlist.append(str(sen[i]))
          wordlist.append(str(sen[i-1]))
          wordlist.append(str(sen[i+1]))
        except:
           pass

      if sen[i].pos_== "PROPN" or sen[i].pos_=="ADP" and str(sen[i])!="See" and str(sen[i])=="cf" and str(sen[i])=="Ltd":
        wordlist.append(str(sen[i]))
    combinedfinal["+".join(wordlist)] = text_match[ele]
  final_set = []
  for key in range(len(combinedfinal)):
    first = list(combinedfinal.keys())[key]
    val = combinedfinal[first]
    max_sim = 0
    data = api_call(first)
    count = data["count"]
    for i in range(0,count):
      try:
        name = return_title(data["results"][i]["frontend_pdf_url"])
        sim_index = similarity_index(name, val)
        if sim_index > max_sim:
          max_sim = sim_index
          max_id = data["results"][i]["id"]
      except:
        pass
    final_set.append(max_id)
  
  return final_set
  # strimg = '\t'.join(map(str, final_set))
  # with open("caselaw_citation_graph.text",'a') as f:
  #   f.write(str(id)+'\t'+strimg+'\n')

def api_id(id):
  API_KEY = "4d969d15b4c1362411a787ca1ebd0d1b0da5e31c"

  response = requests.get(
      'https://api.case.law//v1/cases/?full_case=false&id='+str(id),
    #'https://api.case.law/v1/cases/?court=us&page_size=5000',
    #'https://api.case.law/v1/courts/',
      headers={'Authorization': f'Token {API_KEY}', 'body_format':'json'},
  )
  data = response.json()
  return data

def multiple_cases(json_file):
  soup2 = BeautifulSoup(json_file["casebody"]["data"], "xml")
  bool, lis = check_multi(soup2)
  link = multiple_links(json_file)
  final = []
#print(link)
  for ele in range(len(link)):
    max_sim = 0
    first = list(link.keys())[ele]
    lis = first.split(",")
    for i in lis:
      data = api_id(i)
    #print(i)
      try:
        name = return_title(data["results"][0]["frontend_pdf_url"])
        sim_index = similarity_index(name, link[first])
        if sim_index > max_sim:
          max_sim = sim_index
          max_id = data["results"][0]["id"]
      except:
        pass
    final.append(max_id)

  return final
  # strimg = '\t'.join(map(str, final))
  # with open("multiple_links.txt","a") as f: 
  #   f.write(str(id)+'\t'+strimg+'\n')

file_name = "/content/br_121_114.json"

def run(path):
  start = datetime.now()
  with open(file_name, 'r') as j:
    json_file = json.loads(j.read())
  id = json_file["id"]

  cite_set1 = multiple_cases(json_file)
  cite_set2 = citation_graph_fn(json_file)
  final_lis = cite_set1 + cite_set2 
  final_set = set(final_lis)

  strimg = '\t'.join(map(str, list(final_set)))

  with open ("citation_graph_caselaw.text","a") as f:
    f.write(str(id) + '\t' + strimg + '\n')

  end = datetime.now()
  td = (end - start).total_seconds() * 10**3
  print(f"The time of execution of above program is : {td:.03f}ms")

run(file_name)