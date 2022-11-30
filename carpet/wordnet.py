from nltk.corpus import WordNetCorpusReader, LazyCorpusLoader, CorpusReader
from django.conf import settings
from nltk.corpus import wordnet2021

_wordnet = LazyCorpusLoader(
    settings.WORDNET_NAME,
    WordNetCorpusReader,
    LazyCorpusLoader(
        "omw-1.4",
        CorpusReader,
        r".*/wn-data-.*\.tab",
        encoding="utf8",
    ),
)

wordnet: WordNetCorpusReader = _wordnet # type: ignore
