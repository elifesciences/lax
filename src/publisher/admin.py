from django.contrib import admin
import models

admin_list = [
    (models.Publisher,),
    (models.Journal,),
    (models.Article,) ,
]

[admin.site.register(*t) for t in admin_list]
