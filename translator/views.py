import os
import subprocess
import uuid

from django.conf import settings
from django.http import (
    FileResponse,
    HttpRequest,
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
    langs = (
        list(sorted(best_langs, key=lambda l: req_langs.index(l.text))) + langs
    )
    if request.method == "POST":
        form = TranslationForm(request.POST)
        if form.is_valid():
            lang = LanguageTag.objects.get_from_str(form.cleaned_data["lang"])
            if langs[0] != lang:
                langs.remove(lang)
                langs.insert(0, lang)
            ctx = TranslatorContext(
                key=Key(form.cleaned_data["key"]),
                use_ner=form.cleaned_data["use_ner"],
                show_det=form.cleaned_data["show_det"],
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
            score, speeches = translate(
                ctx,
                form.cleaned_data["text"],
                lang,
                form.cleaned_data["add_lyrics"],
            )
            histories = []
            for speech in speeches:
                for token in speech.span:
                    histories.append(
                        {
                            "token": token,
                            "history": speech.token_history.get(token),
                            "skipped": token in speech.skipped_tokens,
                            "merged_token": speech.merged_tokens.get(token),
                        }
                    )

            uuid4 = str(uuid.uuid4())
            path = os.path.join(settings.M21_OUT_DIR, uuid4)
            mxl_path = score.write("mxl", path)
            subprocess.call(
                [
                    "python3",
                    settings.BASE_DIR / "xml2abc_mod.py",
                    str(mxl_path),
                    "-o",
                    settings.M21_OUT_DIR,
                ]
            )
            with open(path + ".abc") as f:
                return render(
                    request,
                    "translator/index.html",
                    {
                        "langs": langs,
                        "abc": f.read(),
                        "histories": histories,
                        "mxl_url": f"/mxl/{uuid4}/",  # TODO: use reverse
                    },
                )
        else:
            return JsonResponse(form.errors)

    return render(
        request,
        "translator/index.html",
        {"langs": langs, "abc": None, "histories": []},
    )


def mxl(request: HttpRequest, filename):
    filename += ".mxl"
    path = os.path.join(settings.M21_OUT_DIR, filename)
    response = FileResponse(
        open(path, "rb"),
        as_attachment=True,
        filename=filename,
    )
    return response
