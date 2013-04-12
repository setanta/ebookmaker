#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os
import glob
import codecs
from bs4 import BeautifulSoup
from ebookmaker import OPFGenerator, parseEBookFile
from urllib.request import urlopen, urlretrieve

coverFile = 'capa.jpg'
unis = ['', 'i', 'ii', 'iii', 'iv', 'v', 'vi', 'vii', 'viii', 'ix']
dezes = ['', 'x', 'xx', 'xxx']
url = 'http://iliadaemportugues.blogspot.com.br/2009/01/'
url1 = url + 'canto-%s.html'
url2 = url + 'rapsdia-%s.html'
html = '''<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11\
/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
<meta name="author" content="Homero">
<meta name="description" content="Ilíada">
<meta name="classification" content="Poetry" >
<title>Ilíada</title>
<link rel="stylesheet" href="style.css" type="text/css" />
</head>
<body>

'''

def getChapter(bookNum):
    uni = bookNum % 10
    dez = (bookNum - uni) // 10
    romanNum = dezes[dez] + unis[uni]
    url = url1 % romanNum if bookNum < 21 else url2 % romanNum
    print('Obtendo Rapsódia %s' % romanNum.upper())
    data = urlopen(url).read()
    soup = BeautifulSoup(data)

    text = soup.find('div', {'class': 'post-body entry-content'})
    contents = text.contents[:-2]
    if romanNum == 'i':
        contents = contents[9:]
    title = contents[0]
    contents = contents[2:]

    fname = 'rapsodia-%s.html' % romanNum
    with codecs.open(fname, 'w', encoding='utf-8') as outf:
        outf.write(html)
        outf.write('<h1 id="ca' + romanNum + '">' + title.strip() + '</h1>\n\n<p>')
        outf.write(''.join(['</p>\n<p>' if hasattr(tag, 'name') and tag.name == 'br' else str(tag) for tag in contents]).strip())
        outf.write('</p>\n\n</body>\n</html>\n')

def getCover():
    print('Obtendo capa da Wikimedia Commons.')
    url = 'http://upload.wikimedia.org/wikipedia/commons/thumb/1/11/RISD_Sarcophagus_Trojan_War_06.JPG/600px-RISD_Sarcophagus_Trojan_War_06.JPG'
    urlretrieve(url, coverFile)

def clearAcquiredFiles():
    files = glob.glob('rapsodia-*.html')
    for f in files:
        os.remove(f)
    os.remove(coverFile)

def main():
    getCover()
    for i in range(1, 25):
        getChapter(i)
    ebookData = parseEBookFile('iliada.json')
    gen = OPFGenerator(ebookData)
    gen.createEBookFile()
    clearAcquiredFiles()

if __name__ == '__main__':
    main()
