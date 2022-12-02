# Grove

A backend for translating English and other languages into the musical language Maas. Currently in early development.

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

To install, all you need is a Python 3 virtualenv, a Postgres database, and some storage space.
The Celery and Redis stuff isn't done so don't worry about that.

Install requirements:

`pip install --require-virtualenv -r requirements.txt`

Next, set the `DJANGO_DATABASE_URL` environment variable
with the format `postgres://USER:PASSWORD@HOST:PORT/NAME`

Migrate database:

`python manage.py migrate`

Note: you might have to comment the line importing TranslationContext in translator/views.py if you get weird errors.
Just remember to uncomment it before you start translating stuff lol

Load jangle (language tags) data:

`python manage.py loadjangledata`

Download the wordnet and register Maas & Carpet data:

```
python manage.py shell
>>> import nltk
>>> nltk.download("wordnet")
>>> nltk.download("wordnet2021")
>>> from maas.registration import register_full_lexicon
>>> register_full_lexicon()
>>> from carpet.registration import register_dictionaries
>>> register_dictionaries()
```

Note: you can run register_dictionaries and register_full_lexicon again if you've changed any definitions or added any lexicons!

Next, extract `corpora/wordnet.zip` (usually in nltk_data in your home dir) into `corpora` and `corpora/wordnet2021`.
Hopefully this won't be necessary after the next nltk release ([see this gh issue](https://github.com/nltk/nltk/issues/30510))

Load some fixtures:

`python manage.py loaddata translator/fixtures/spacy.yaml`

Make a superuser:

`python manage.py createsuperuser`

Run server:

`python manage.py runserver`

Go to http://localhost:8000/admin/translator/spacylanguage/ and save any SpaCy language models you'll be using.
Install them with the &quot;Download SpaCy package&quot; action.
I recommend using medium-sized models (check out https://spacy.io/models)

Finally, you can go to localhost:8000 and start screwing around!

Note: English is currently the only language with lexeme translations written,
so for other languages write some (please!) in maas/lexicon
or disable lexeme lyrics in the translator's advanced settings.

## Some Software Used

All libraries and programs used are FOSS (free open-source software), with the exception of Google Translate, used for languages unsupported by SpaCy or the Open Multilingual Wordnet. (WIP)

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

### Redis

- [Official Site](https://redis.io/)

### SpaCy

- [Official Site](https://spacy.io/)
- [PyPI](https://pypi.org/project/spacy/)
- [Source](https://github.com/explosion/spaCy)

### Uvicorn

- [Homepage](https://www.uvicorn.org/)
- [PyPI](https://pypi.org/project/uvicorn/)
- [Source](https://github.com/encode/uvicorn/)

### xmlplay

- [Homepage](https://wim.vree.org/js3/xmlplay_index.html)

---

A product of [The Null Identity](https://society.nullring.xyz/).
