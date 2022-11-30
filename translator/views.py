from langcodes import standardize_tag
from django.shortcuts import render
from django.http import JsonResponse
from translator.meta import (
    get_supported_languages,
)


def supported_languages(request):
    print(type(request))
    return JsonResponse({})
