import enum
import spacy
from django.conf import settings
from moss.models import CarpetPhrase, Definition, PosTag
from string import ascii_lowercase

nlp = spacy.load(settings.SPACY_PACKAGE)

WORD_CHARS = ascii_lowercase + '_\':'
SHOW_BRACES = False
SHOW_PARANTHESES = False

class ToneChange(enum.Enum):
    UP = '+'
    DOWN = '-'
    LAST = '@'
    UNISON = None

class Depth(enum.IntEnum):
    SIMPLE = 0
    SHALLOW = 1
    RECURSIVE = 2
    VOCAB = 3
    EXTEND_VOCAB = 4


class AbstractPhrase:
    phrase_str = ''
    def __init__(self,
        has_braces = False,
        tone_changes = '',
        suffixes = '',
        multiplier = 1,
        ):
        self.has_braces = has_braces
        self.tone_changes = tone_changes
        self.suffixes = suffixes
        self.multiplier = multiplier
    
    def unwrapped_str(self) -> str:
        return self.phrase_str

    def __str__(self):
        start_char = ''
        end_char = ''
        if SHOW_BRACES and self.has_braces:
            start_char = '{'
            end_char = '}'
        elif SHOW_PARANTHESES and self.suffixes and ' ' in self.phrase:
            start_char = '('
            end_char = ')'
        return ((self.tone_changes +
            start_char +
            self.unwrapped_str() +
            end_char +
            self.suffixes +
            ' ') * self.multiplier)[:-1]
    
def def_to_model_kwargs(term: str, infer_pos_tag=False, pos_tag_as_obj=False) -> dict[str]:
    kwargs = dict()
    kwargs['term'] = term.strip().lower().replace('_', ' ')
    if ':' in term:
        kwargs['pos_tag__abr'], kwargs['term'] = kwargs['term'].split(':')
        kwargs['pos_tag__abr'] = kwargs['pos_tag__abr'].upper()
    elif infer_pos_tag:
        kwargs['pos_tag__abr'] = nlp(term)[0].pos_
    if kwargs.get('pos_tag__abr') and pos_tag_as_obj:
        kwargs['pos_tag'] = PosTag.objects.get(abbr=kwargs.pop('pos_tag__abr'))        
    return kwargs

class AbstractParentPhrase(AbstractPhrase):
    def __init__(self, *args, **kwargs):
        self.children = []
        return super().__init__(*args, **kwargs)

    def extend(self, depth=Depth.VOCAB):
        if depth < Depth.SHALLOW:
            return
        self.children = []
        self._extend(depth)
        if depth < Depth.RECURSIVE:
            return
        for i, child in enumerate(self.children):
            if issubclass(type(child), AbstractPhrase):
                if child.has_braces or len(self.children) == 1:
                    self.children[i].multiplier *= self.multiplier
                    self.children[i].suffixes += self.suffixes
                    self.multiplier = 1
                    self.suffixes = ''
                if depth >= Depth.RECURSIVE:
                    child.extend(depth)
            
    def unwrapped_str(self):
        return ' '.join(map(str, self.children)) or self.phrase_str


class DefinitionPhrase(AbstractParentPhrase):
    def __init__(self, obj: Definition, *args, **kwargs):
        self.def_obj = obj
        return super().__init__(*args, **kwargs)
    
    def _extend(self, depth=Depth.VOCAB):
        if depth < Depth.EXTEND_VOCAB:
            self.phrase_str = self.def_obj.term
        elif self.def_obj.core_synonym:
            self.phrase_str = self.def_obj.core_synonym.term
        elif self.def_obj.carpet_phrase:
            self.children = [ModelPhrase(self.def_obj.carpet_phrase)]


class ModelPhrase(AbstractParentPhrase):
    def __init__(self, obj: CarpetPhrase, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.obj = obj
        self.has_braces = obj.has_braces
        self.tone_changes = obj.tone_changes
        self.suffixes = obj.suffixes
        self.multiplier = obj.multiplier
        
    def _extend(self, depth=Depth.VOCAB):
        if self.obj.definition_child:
            self.obj.children = [DefinitionPhrase(self.obj, depth)]
        for child in self.obj.get_children():
            self.children.append(ModelPhrase(child.carpet_child))


class StrPhrase(AbstractParentPhrase):
    def __init__(self, phrase='', *args, **kwargs):
        self.phrase_str = phrase.strip().lower()
        return super().__init__(*args, **kwargs)
    
    def _extend(self, depth=Depth.VOCAB):
        is_term = True
        for char in self.phrase_str:
            if char not in WORD_CHARS:
                is_term = False
                break
        
        if is_term:
            if depth >= Depth.VOCAB:
                self.children = [DefinitionPhrase(
                    Definition.objects.get(**def_to_model_kwargs(self.phrase_str))
                )]
        else:        
            child = StrPhrase()
            parentheses_depth = 0
            braces_depth = 0
            is_multiplying = False
            multiplier_str = ''

            for char in self.phrase_str + ' ':
                if char == '(':
                    if parentheses_depth: child.phrase_str += char
                    parentheses_depth += 1
                elif char == ')':
                    parentheses_depth -= 1
                    if parentheses_depth: child.phrase_str += char
                elif char == '{':
                    if braces_depth: child.phrase_str += char
                    else: child.has_braces = True
                    braces_depth += 1
                elif char == '}':
                    braces_depth -= 1
                    if braces_depth: child.phrase_str += char
                elif parentheses_depth or braces_depth:
                    child.phrase_str += char
                elif not child.phrase_str and char in [e.value for e in ToneChange]:
                    child.tone_changes += char
                elif char == '*':
                    is_multiplying = True
                elif char in WORD_CHARS:
                    child.phrase_str += char
                elif char.isspace():
                    if multiplier_str:
                        child.multiplier *= int(multiplier_str)
                    if len(child.phrase_str) > 0:
                        self.children.append(child)
                    child = StrPhrase()
                    parentheses_depth = 0
                    braces_depth = 0
                    is_multiplying = False
                    multiplier_str = ''
                elif is_multiplying and char.isdigit():
                    multiplier_str += char
                else:
                    child.suffixes += char

# recursive
def save_definition(phrase: AbstractParentPhrase, parent=None, index=0) -> CarpetPhrase:
    if hasattr(phrase, 'obj'):
        return

    obj = CarpetPhrase.objects.create(
        parent = parent,
        index = index,
        has_braces = phrase.has_braces,
        tone_changes = phrase.tone_changes,
        suffixes = phrase.suffixes,
        multiplier = phrase.multiplier,
        definition_child = getattr(phrase, 'def_obj', None)
    )

    for i, child in enumerate(phrase.children):
        phrase.children[i].obj = save_definition(child, obj, i)
    
    return obj


