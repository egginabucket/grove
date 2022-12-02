from django.shortcuts import render
from django.http import JsonResponse, HttpResponseNotAllowed, HttpRequest
from translator.meta import get_supported_languages
from translator.translator import TranslatorContext, translate
from translator.forms import TranslationForm
from music21.key import Key
from music21.tinyNotation import Converter
from jangle.models import LanguageTag
import subprocess
from django.conf import settings

def index(request: HttpRequest):
    if request.method == "POST":
        form = TranslationForm(request.POST)
        if form.is_valid():
            lang = LanguageTag.objects.get_from_str(form.cleaned_data["lang"])
            ctx = TranslatorContext(
                key=Key(form.cleaned_data["key"]),
                write_slurs=form.cleaned_data["write_slurs"],
                gender_pronouns=form.cleaned_data["gender_pronouns"],
                sub_rel_ents=form.cleaned_data["sub_rel_ents"],
                hypernym_search_depth=form.cleaned_data["hyper_search_depth"],
                hyponym_search_depth=form.cleaned_data["hypo_search_depth"],
                max_l_grouping=form.cleaned_data["max_l_grouping"],
                max_r_grouping=form.cleaned_data["max_r_grouping"],
                peri_rest=form.cleaned_data["peri_rest"],
                comm_rest=form.cleaned_data["comm_rest"],
                lexeme_fallback=Converter(
                    form.cleaned_data["lexeme_fallback"], makeNotation=False
                )
                .parse()
                .stream,
            )
            score = translate(
                ctx,
                form.cleaned_data["text"],
                lang,
                form.cleaned_data["add_lyrics"],
            )
            path = score.write("mxl")
            subprocess.call(["python3", settings.BASE_DIR / "xml2abc_mod.py", str(path), "-o", str(path.parent)])
            with open(str(path).replace(".mxl", ".abc")) as f:
                return render(
                    request,
                    "translator/index.html",
                    {"langs": get_supported_languages(), "abc": f.read()},
                )
        else:
            return JsonResponse(form.errors)

    return render(
        request,
        "translator/index.html",
        {"langs": get_supported_languages(), "abc": None},
    )


def re(request):
    print(type(request))
    return JsonResponse({})
