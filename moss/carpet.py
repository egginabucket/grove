import enum
from moss.models import CarpetPhrase, Definition
from string import ascii_lowercase

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

    def __str__(self, phrase: str):
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
            phrase +
            end_char +
            self.suffixes +
            ' ') * self.multiplier)[:-1]
    
def def_to_model_kwargs(term: str) -> dict[str]:
    kwargs = dict()
    term = term.strip().upper()
    if ':' in term:
        kwargs['tag'], term = term.split(':')
    kwargs['term'] = term.replace('_', ' ').lower()
    return kwargs

class AbstractParentPhrase(AbstractPhrase):
    children = []
    contains_braces = False

    def extend(self, depth=Depth.VOCAB):
        return
    
    def extend_children(self, depth=Depth.VOCAB):
        if depth < Depth.RECURSIVE:
            return
        for i, child in enumerate(self.children):
            if issubclass(type(child), type(self)):
                if child.has_braces or len(self.children) == 1:
                    self.children[i].multiplier *= self.multiplier
                    self.children[i].suffixes += self.suffixes
                    self.multiplier = 1
                    self.suffixes = ''
                child.extend()
            
    def unwrapped_str(self):
        return ' '.join(map(str, self.children)) or self.phrase_str

    """
    def steal_properties(self, phrase):
        self.has_braces = phrase.has_braces
        self.tone_changes += phrase.tone_changes
        self.suffixes = phrase.suffixes
        self.multiplier = phrase.multiplier
        """

class DefinitionPhrase(AbstractParentPhrase):
    def __init__(self, obj: Definition, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.def_obj = obj
    
    def extend(self, depth=Depth.VOCAB):
        if depth < Depth.VOCAB:
            self.phrase_str = self.def_obj.term
        elif self.def_obj.core_synonym:
            self.phrase_str = self.def_obj.core_synonym.term
        elif self.def_obj.carpet_phrase:
            self.children = [ModelPhrase(self.def_obj.carpet_phrase)]
        self.extend_children(depth)


class ModelPhrase(AbstractParentPhrase):
    def __init__(self, obj: CarpetPhrase, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.obj = obj
        self.has_braces = obj.has_braces
        self.tone_changes = obj.tone_changes
        self.suffixes = obj.suffixes
        self.multiplier = obj.multiplier
        
    def extend(self, depth=Depth.VOCAB):
        if self.obj.definition_child:
            self.obj.children = [DefinitionPhrase(self.obj, depth)]
        for child in self.obj.get_children():
            self.children.append(ModelPhrase(child.carpet_child))
        
        self.extend_children(depth)
    


class StrPhrase(AbstractParentPhrase):
    def __init__(self, phrase='', *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def extend(self, depth=Depth.VOCAB):
        self.phrase = self.phrase.strip().lower()
        is_term = True
        for char in self.phrase:
            if char not in WORD_CHARS:
                is_term = False
                break
        
        if is_term:
            if depth >= Depth.VOCAB:
                self.children = [DefinitionPhrase(
                    Definition.objects.get(**def_to_model_kwargs(self.phrase))
                )]
            else:
                self.phrase_str = self.phrase
        else:
            child = StrPhrase()
            parentheses_depth = 0
            braces_depth = 0
            is_multiplying = False
            multiplier_str = ''

            for char in self.phrase + ' ':
                if char == '(':
                    if parentheses_depth: child.phrase += char
                    parentheses_depth += 1
                elif char == ')':
                    parentheses_depth -= 1
                    if parentheses_depth: child.phrase += char
                elif char == '{':
                    if braces_depth: child.phrase += char
                    else: child.has_braces = True
                    braces_depth += 1
                elif char == '}':
                    braces_depth -= 1
                    if braces_depth: child.phrase += char
                elif parentheses_depth or braces_depth:
                    child.phrase += char
                elif not child.phrase and char in [e.value for e in ToneChange]:
                    child.tone_changes += char
                elif char == '*':
                    is_multiplying = True
                elif char in WORD_CHARS:
                    child.phrase += char
                elif char.isspace():
                    if multiplier_str:
                        child.multiplier *= int(multiplier_str)
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
        self.extend_children(depth)

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


