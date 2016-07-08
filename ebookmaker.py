#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import html
import json
from glob import glob
from string import Template
from bs4 import BeautifulSoup
from zipfile import ZipFile, ZIP_STORED
from argparse import ArgumentParser, ArgumentTypeError

scriptDir, _ = os.path.split(os.path.realpath(__file__))
templateDir = 'opf-templates'

def loadTemplate(templateFile):
    return Template(open(os.path.join(scriptDir, templateDir, templateFile), 'r').read())

templates = {
    'cover' : loadTemplate('template-cover.html'),
    'title' : loadTemplate('template-title-page.html'),
    'toc'   : loadTemplate('template-toc.html'),
    'ncx'   : loadTemplate('template-toc.ncx'),
    'opf'   : loadTemplate('template-content.opf')
}

class Indentor:
    INDENT = '    '
    def __init__(self, level=0):
        self.level = level
    def __enter__(self):
        self.level +=1
        return self
    def __exit__(self, type, value, traceback):
        self.level -= 1
        return False
    def indentation(self, adjust=0):
        return Indentor.INDENT * (self.level + adjust)


class Generator(object):
    def __init__(self, ebookData):
        self.ebook = ebookData
        self.baseDir = os.path.dirname(self.ebook['filename'])

        self.initEBookContentsLists()

        self.outline = {}
        depth = self.ebook['toc']['depth']
        for item in self.ebook['contents']:
            if not item['type'] in self.ebook['toc']['parse']:
                continue
            fname = item['source']
            self.outline[fname] = self.outlineEBookContents(fname, depth)

        images = set()
        for item in self.ebook['contents']:
            if item['generate']:
                continue
            images.update(self.collectImagesFromEBookContents(item['source']))
        self.images = sorted(list(images))

    def outlineEBookContents(self, htmlFile, depth):
        with open(htmlFile, encoding='utf-8', mode='r') as f:
            soup = BeautifulSoup(f.read())
            hTags = ('h1', 'h2', 'h3', 'h4', 'h5', 'h6')
            outline = [h for h in soup.body if getattr(h, 'name', None) in hTags and int(h.name[-1]) <= depth]
            for h in outline:
                for br in h.findAll('br'):
                    lineBreakReplacement = ' '
                    if 'replaceLineBreakWith' in self.ebook['toc']['generate']:
                        lineBreakReplacement = self.ebook['toc']['generate']['replaceLineBreakWith']
                    br.replaceWith(lineBreakReplacement)
            return outline

    def collectImagesFromEBookContents(self, htmlFile):
        with open(htmlFile, encoding='utf-8', mode='r') as f:
            soup = BeautifulSoup(f.read())
            x = [img['src'] for img in soup.body.findAll('img') if img.has_attr('src')]
            return x

    def initEBookContentsLists(self):
        self.tocList = []
        for i in self.ebook['contents']:
            item = i['source']
            if i['type'] in self.ebook['toc']['parse']:
                self.tocList.append(item)

    def createEBookFile(self, ebookFile=None):
        raise NotImplementedError


class OPFGenerator(Generator):

    EPUB_CONTAINER = '''
<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
    </rootfiles>
</container>
'''.strip()

    def __init__(self, ebookData):
        Generator.__init__(self, ebookData)

    def generateHtmlCover(self):
        return templates['cover'].substitute(title=html.escape(self.ebook['title'], True),
                                             coverimage=self.ebook['cover'])

    def generateHtmlTitlePage(self):
        return templates['title'].substitute(title=self.ebook['title'],
                                             author=self.ebook['authors'][0]['name'])

    def generateHtmlToCPage(self):
        tocTxt = ''
        for fileName in self.tocList:
            tocTxt += '<div style="margin-top: 1em;">\n'
            for hTag in self.outline[fileName]:
                url = fileName + '#' + hTag.get('id') if hTag.has_attr('id') else fileName
                tocTxt += '<p style="text-indent: %dem;"><a href="%s">%s</a></p>\n' % \
                            (int(hTag.name[-1]), url, hTag.text)
            tocTxt += '</div>\n'

        tocTitle = self.ebook['toc']['generate']['title']
        return templates['toc'].substitute(title=tocTitle, toc=tocTxt)

    def generateNcx(self):
        ncxDict = {
            'title'     : self.ebook['title'],
            'author'    : self.ebook['authors'][0]['name'],
            'bookid'    : 'BookId', #self.ebook['identifier']['id'],
            'depth'     : self.ebook['toc']['depth']
        }
        indentor = Indentor(-1)
        global counter
        counter = 0
        def generateSection(fileName, tocItems, level):
            global counter
            nav = ''
            with indentor as ind:
                for index, hTag in enumerate(tocItems):
                    hLevel = int(hTag.name[-1])
                    if hLevel < level:
                        return
                    counter += 1
                    nav += ind.indentation()
                    nav += '<navPoint id="nav{0}" playOrder="{0}">\n'.format(counter)
                    url = fileName + '#' + hTag.get('id') if hTag.has_attr('id') else fileName
                    with indentor as ind:
                        nav += ind.indentation()
                        nav += '<navLabel><text>%s</text></navLabel>\n' % hTag.text
                        nav += ind.indentation()
                        nav += '<content src="%s"/>\n' % url
                    if index + 1 < len(tocItems):
                        nextHTag = tocItems[index + 1]
                        nextHLevel = int(nextHTag.name[-1])
                        if nextHLevel > level:
                            nav += generateSection(fileName, tocItems[index + 1:], nextHLevel)
                    nav += ind.indentation() + '</navPoint>\n'
            return nav

        nav = ''
        for fileName in self.tocList:
            nav += generateSection(fileName, self.outline[fileName], 1)
        ncxDict['navpoints'] = nav
        return templates['ncx'].substitute(ncxDict)

    def generateOpf(self):
        opfDict = {
            'title' : self.ebook['title'],
            'author' : self.ebook['authors'][0]['name'],
            'authorOpfFileAs' : '',
            'rights' : self.ebook['rights'],
            'bookId' : 'bookId',#self.ebook['identifier']['id'],
            'idOpfScheme' : self.ebook['identifier']['scheme'].upper(),
            'idValue' : self.ebook['identifier']['value'],
            'publisher' : self.ebook['publisher'],
            'lang' : self.ebook['language'],
            'coverMetaLine' : '',
            'imagesMetaLine' : '',
            'manifestCoverLine' : '',
            'manifestContents' : '',
            'spineContents' : '',
            'guideSection' : ''
        }

        if 'sort' in self.ebook['authors'][0]:
            opfDict['authorOpfFileAs'] = 'opf:file-as="%s" ' % \
                                         self.ebook['authors'][0]['sort']

        def getImageLine(image, itemId):
            _, ext = os.path.splitext(image)
            mime = ext[1:]
            if mime == 'jpg':
                mime = 'jpeg'
            return '<item id="%s" href="%s" media-type="image/%s"/>\n' % (itemId, image, mime)

        if 'cover' in self.ebook:
            opfDict['coverMetaLine'] = '<meta name="cover" content="coverimage" />'
            opfDict['manifestCoverLine'] = getImageLine(self.ebook['cover'], 'coverimage')

        for i, image in enumerate(self.images):
            opfDict['imagesMetaLine'] += Indentor.INDENT + getImageLine(image, 'image%d' % i)

        for i, item in enumerate(self.ebook['contents']):
            fileName = item['source']
            opfDict['manifestContents'] += \
                    '%s<item id="item%d" media-type="application/xhtml+xml" href="%s"/>\n' % \
                    (Indentor.INDENT, i, item['source'])
            opfDict['spineContents'] += '%s<itemref idref="item%d"/>\n' % (Indentor.INDENT, i)

        if 'guide' in self.ebook:
            opfDict['guideSection'] = '<guide>\n'
            for ref in self.ebook['guide']:
                opfDict['guideSection'] += Template(Indentor.INDENT + \
                    '<reference type="$type" title="$title" href="$href"/>\n' \
                ).substitute(ref)
            opfDict['guideSection'] += '</guide>\n'

        return templates['opf'].substitute(opfDict)

    def createEBookFile(self, ebookFile=None):
        if not ebookFile:
            ebookFile = '%s.epub' % os.path.join(self.baseDir, self.ebook['filename'])

        print('Generating ePub file for eBook "%s".' % self.ebook['title'])

        epubFile = ZipFile(ebookFile, 'w')

        # Write mimetype file.
        epubFile.writestr('mimetype', 'application/epub+zip', ZIP_STORED)

        # Write META-INF directory and contents.
        epubFile.writestr(os.path.join('META-INF', 'container.xml'),
                          OPFGenerator.EPUB_CONTAINER, ZIP_STORED)

        # Add book cover image.
        if 'cover' in self.ebook:
            coverFile = os.path.join('OEBPS', self.ebook['cover'])
            epubFile.write(self.ebook['cover'], coverFile)

        # Add images.
        for image in self.images:
            imageFile = os.path.join('OEBPS', image)
            epubFile.write(image, imageFile)

        # Add style sheet file.
        style = os.path.join('OEBPS', 'style.css')
        epubFile.write('style.css', style, ZIP_STORED)

        # Add content files.
        for item in self.ebook['contents']:
            fileName = item['source']

            if not item['generate']:
                dstFile = os.path.join('OEBPS', fileName)
                epubFile.write(fileName, dstFile, ZIP_STORED)
                continue

            if item['type'] == 'cover':
                dstFilename = os.path.join('OEBPS', fileName)
                dstContents = self.generateHtmlCover()
            elif item['type'] == 'toc':
                dstFilename = os.path.join('OEBPS', fileName)
                dstContents = self.generateHtmlToCPage()
            elif item['type'] == 'title-page':
                dstFilename = os.path.join('OEBPS', fileName)
                dstContents = self.generateHtmlTitlePage()
            else:
                continue
            epubFile.writestr(dstFilename, dstContents, ZIP_STORED)

        # Write OPF file.
        opfFile = os.path.join('OEBPS', 'content.opf')
        epubFile.writestr(opfFile, self.generateOpf(), ZIP_STORED)

        # Write NCX index.
        ncxFile = os.path.join('OEBPS', 'toc.ncx')
        epubFile.writestr(ncxFile, self.generateNcx(), ZIP_STORED)

        epubFile.close()

        print('ePub file "%s" successfully generated.' % ebookFile)


def parseEBookFile(ebookFile):
    try:
        data = json.load(open(ebookFile, 'r'))
        hasCoverPage = False
        for item in data['contents']:
            # Set generate flag for content item.
            if not 'generate' in item:
                if item['type'] == 'toc' and 'generate' in data['toc']:
                    item['generate'] = True
                else:
                    item['generate'] = False

            # Expand wild cards.
            if item['type'] == 'text' and '*' in item['source']:
                files = sorted(glob(item['source']))
                if not files:
                    raise ArgumentTypeError('\nCan\'t find files from expression: %r' % \
                                            item['source'])
                idx = data['contents'].index(item)
                for f in files:
                    newItem = {
                        'type' : item['type'],
                        'source' : f,
                        'generate' : False
                    }
                    data['contents'].insert(idx, newItem)
                    idx += 1
                del data['contents'][idx]

            if item['type'] == 'cover':
                hasCoverPage = True

        if not hasCoverPage and 'cover' in data:
            coverItem = {
                'type' : 'cover',
                'source' : 'cover.html',
                'generate' : True
            }
            data['contents'].insert(0, coverItem)

    except IOError as e:
        raise ArgumentTypeError('\n%s' % e)
    except ValueError as e:
        raise ArgumentTypeError('\n[JSON parser] %s' % e)
    return data

def main():
    parser = ArgumentParser(description='Generates ebooks from a description file.')
    parser.add_argument('-o', '--output', type=str,
                        help='Name of the output file.')
    parser.add_argument('ebookData', type=parseEBookFile,
                        help='JSON file containing the ebook information.')

    args = vars(parser.parse_args())

    gen = OPFGenerator(args['ebookData'])
    gen.createEBookFile(args['output'])

if __name__ == '__main__':
    main()
