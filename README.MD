# Grove

A translator for English and other languages into the musical language Maas, built with SpaCy and the Open Multilingual Wordnet.

---

## Maas

Maas (formerly known as Moss) is a constructed musical language, like Solresol.
Created by Jackson Moore of the &quot;Bruce High Quality Foundation University&quot;,
what little information of it that remains online is preserved on the Wayback Machine.

- [thelanguageofmoss.com Mar 2018 archive](https://web.archive.org/web/20180311194718/http://www.thelanguageofmoss.com/)
- [thelanguageofmoss.com Aug 2009 archive](https://web.archive.org/web/20090813110752/http://www.thelanguageofmoss.com/) - includes a mostly complete dictionary
- [Wikipedia Article](<https://en.wikipedia.org/wiki/Moss_(language)>)
- [page on maas on Moore's personal site](http://jacksonmoore.net/a/maas.html)

## Installation

Grove is still in very early development.
Hopefully there will be an actual site to visit soon,
but until then, I might make a dockerfile if somebody bugs me enough.

To install you need a Python 3 virtualenv, a Postgres database, and some storage space.
The Celery and Redis stuff isn't done so don't worry about that.

Install requirements:

`pip install --require-virtualenv -r requirements.txt`

Next, set the `DATABASE_URL` environment variable
with the format `postgres://USER:PASSWORD@HOST:PORT/NAME`

Migrate database:

`python manage.py migrate`

Load jangle (language tags) data:

`python manage.py loadjangledata`

Load the Maas lexicon:

`python manage.py loadlexicon --native-to-en`
(use -h for more info)

Download the WordNet:

```
python
>>> import nltk
>>> nltk.download(['omw-1.4', 'wordnet', 'wordnet2021'])
```

Next, go to your nltk_data folder (usually in your home folder) and extract
`corpora/wordnet2021.zip` into `corpora`,
and `corpora/wordnet.zip` into `corpora` and the new `corpora/wordnet2021` folder.
Unfortunately the new fix for this
([see this issue](https://github.com/nltk/nltk/issues/30510))
in NLTK 3.8 doesn't seem to work with OMW :(

Register the dictionary:

`python manage.py loaddictionary`
(use -h for more info)

Load some fixtures:

`python manage.py loaddata translator/fixtures/spacy.yaml`

Download SpaCy packages:

`python manage.py loadspacymodels dev -d`
(use -h for more info)

Feel free to replace `dev` with any of the files in translator/spacy-models or the given directory, just be wary of storage use.

Make a superuser:

`python manage.py createsuperuser`

Run server:

Set the
WEB_CONCURRENCY,
DJANGO_SECRET_KEY,
M21_OUT_DIR,
CSRF_ALLOWED_ORIGINS,
and CORS_ALLOWED_ORIGINS
environment variables
and `./runserver.sh`

Or `python manage.py runserver` for dev.

Note: English is currently the only language with lexeme translations written,
so for other languages write some (please!) in maas/lexicon
or disable lexeme lyrics in the translator's advanced settings.

## Some Software Used

All libraries and programs used are FOSS (free open-source software), with the exception of Google Translate, used for languages unsupported by SpaCy or the Open Multilingual Wordnet. (WIP)

REFERENCES COMING SOON

### Celery

- [Docs](https://docs.celeryq.dev/en/stable/index.html)
- [PyPI](https://pypi.org/project/celery/)
- [Source](https://github.com/celery/celery)

### Django

- [Homepage](https://www.djangoproject.com/)
- [PyPI](https://pypi.org/project/Django/)
- [Source](https://github.com/django/django)

### Gunicorn

- [Homepage](https://gunicorn.org/)
- [PyPI](https://pypi.org/project/gunicorn/)
- [Source](https://github.com/benoitc/gunicorn)

### music21

- [Homepage](https://web.mit.edu/music21/)
- [Docs](https://web.mit.edu/music21/doc/index.html)
- [PyPI](https://pypi.org/project/music21/)
- [Source](https://github.com/cuthbertLab/music21/)

### Natural Language Toolkit (NLTK)

- [Official Site](https://www.nltk.org/)
- [PyPI](https://pypi.org/project/nltk/)
- [Source](https://github.com/nltk/nltk)

### Open English WordNet

- [Official Site](https://en-word.net/)
- [Source](https://github.com/globalwordnet/english-wordnet)

### Open Multilingual Wordnet

- [Original Site (down)](http://compling.hss.ntu.edu.sg/omw/)
- [Blog Post](https://blogs.ntu.edu.sg/dh/project/open-multilingual-wordnet/)

### Redis

- [Official Site](https://redis.io/)
- [Source](https://github.com/redis/redis)

### SpaCy

- [Official Site](https://spacy.io/)
- [PyPI](https://pypi.org/project/spacy/)
- [Source](https://github.com/explosion/spaCy)

### Uvicorn

- [Homepage](https://www.uvicorn.org/)
- [PyPI](https://pypi.org/project/uvicorn/)
- [Source](https://github.com/encode/uvicorn/)

### xml2abc

- [Homepage](https://wim.vree.org/svgParse/xml2abc.html)

### xmlplay

- [Homepage](https://wim.vree.org/js3/xmlplay_index.html)

---

A product of [The Null Identity](https://society.nullring.xyz/).
