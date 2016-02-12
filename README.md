ebookmaker
==========

ebookmaker is a Python 3 script that takes a JSON book description
and a bunch of HTML files, and builds an eBook.
The script generates the boring part of the eBook metadata, e.g.
the index that appears both in contents.opf, toc.ncx, and
in an HTML page.

The script depends on the
[beautifulsoup4](https://pypi.python.org/pypi/beautifulsoup4/4.3.2)
package.

To allow the script to generate the various tables of contents
(= content.opf, toc.ncx, and the HTML index; the last one
may be done by hand, if desired) the HTML content must follow a couple
of simple rules:

* Use header tags consistently: `<h1>` for section/chapter,
  `<h2>` for subsection, `<h3>` for subsubsection.
* Use the `"id"` attribute to identify the entry in the index.

Examples
--------

In the future I'll document the JSON book description format,
but for now there are a couple of books in the examples directory.
Enter the examples directory and run the script like this to
build EPUB files:

    $ python3 ../../ebookmaker BOOK.json

Recipes
-------

The 'recipes' directory is also interesting. There you'll find
Python scripts that download content not available in ebook format,
but as HTML, format it and call on ebookmaker to assemble in a
nice ebook.

Usage
-----

    ebookmaker [-h] [-o OUTPUT] ebookData

positional arguments:

    ebookData             JSON file containing the ebook information.

optional arguments:

    -h, --help            show this help message and exit
    -o OUTPUT,            Name of the output file.
    --output OUTPUT

