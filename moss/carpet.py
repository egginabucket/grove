import enum
from moss.models import CarpetPhrase, Definition
from string import ascii_lowercase

WORD_CHARS = ascii_lowercase + '_\''
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
    

    def wrap_str(self, phrase: str) -> str:
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
    


class AbstractParentPhrase(AbstractPhrase):
    children = []
    contains_braces = False

    def extend(self, depth=Depth.VOCAB):
        return
    
    def extend_children(self, depth=Depth.VOCAB):
        for i, child in enumerate(self.children):
            if issubclass(type(child), type(self)):
                if child.has_braces or len(self.children) == 1:
                    self.children[i].multiplier *= self.multiplier
                    self.children[i].suffixes += self.suffixes
                    self.multiplier = 1
                    self.suffixes = ''
                child.extend()
        if len(self.children) == 1:
            self.children = self.children[0].children
            
            

    def __str__(self):
        return self.wrap_str(' '.join(map(str, self.children)))

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
        self.obj = obj
    
    def extend(self, depth=Depth.VOCAB):
        if depth < Depth.VOCAB or self.obj.core_synonym:
            self.children = [self.obj.term]
            return
        if self.obj.definition.synonym:
            self.children = [DefinitionPhrase(self.obj)]
        elif self.obj.carpet_phrase:
            self.children = [ModelPhrase(self.obj.carpet_phrase)]
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
            self.children = [
                DefinitionPhrase(Definition.objects.get(term=self.phrase.replace('_',  ' ')))
            ]
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
        self.extend_children()
