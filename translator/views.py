import os
import subprocess
import uuid

from django.conf import settings
from django.http import (
    FileResponse,
    HttpRequest,
    HttpResponseNotAllowed,
    JsonResponse,
)
from django.shortcuts import render
from django.urls import reverse
from jangle.models import LanguageTag
from music21.key import Key
from music21.tinyNotation import Converter

from translator.forms import TranslationForm
from translator.meta import get_supported_languages
from translator.translator import TranslatorContext, translate


def index(request: HttpRequest):
    req_langs = [
        l.split(";")[0]
        for l in request.headers.get("Accept-Language", "en").split(",")
    ]
    langs = []
    best_langs = []
    for lang in get_supported_languages():
        if lang.text in req_langs:
            best_langs.append(lang)
        else:
            langs.append(lang)
    langs = sorted(best_langs, key=lambda l: req_langs.index(l.text)) + langs
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
                .stream.flatten(),
            )
            score = translate(
                ctx,
                form.cleaned_data["text"],
                lang,
                form.cleaned_data["add_lyrics"],
            )
            uuid4 = str(uuid.uuid4())
            path = score.write(
                "mxl", os.path.join(settings.M21_OUT_DIR, uuid4)
            )
            subprocess.call(
                [
                    "python3",
                    settings.BASE_DIR / "xml2abc_mod.py",
                    str(path),
                    "-o",
                    settings.M21_OUT_DIR,
                ]
            )
            with open(str(path).removesuffix(".mxl") + ".abc") as f:
                return render(
                    request,
                    "translator/index.html",
                    {
                        "langs": langs,
                        "abc": f.read(),
                        "mxl_url": f"/mxl/{uuid4}/",  # TODO: use reverse
                    },
                )
        else:
            return JsonResponse(form.errors)

    return render(
        request,
        "translator/index.html",
        {"langs": langs, "abc": None},
    )


def mxl(request: HttpRequest, filename):
    filename += ".mxl"
    response = FileResponse(
        open(settings.M21_OUT_DIR / filename, "rb"),
        as_attachment=True,
        filename=filename,
    )
    return response
