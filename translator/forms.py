from django import forms

class TranslationForm(forms.Form):
    lang = forms.CharField()
    text = forms.CharField()
    write_slurs = forms.BooleanField(required=False)
    add_lyrics = forms.BooleanField(required=False)
    sub_rel_ents = forms.BooleanField(required=False)
    gender_pronouns = forms.BooleanField(required=False)
    hyper_search_depth = forms.IntegerField(max_value=5, min_value=0)
    hypo_search_depth = forms.IntegerField(max_value=3, min_value=0)
    max_l_grouping = forms.IntegerField(max_value=4, min_value=0)
    max_r_grouping = forms.IntegerField(max_value=4, min_value=0)
    key = forms.CharField()
    deg_offset = forms.IntegerField()
    phrase_up_deg = forms.IntegerField(min_value=0)
    phrase_down_deg = forms.IntegerField(max_value=0)
    lexeme_fallback = forms.CharField()
    peri_rest = forms.FloatField(min_value=0)
    comm_rest = forms.FloatField(min_value=0)
