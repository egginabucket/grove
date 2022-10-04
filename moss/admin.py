from django.contrib import admin

from moss.models import *

admin.site.register([
    PosTag,
    CoreDefinition,
    Definition,
    CarpetPhrase,
])