from django.contrib import admin
from .models import establishments, patrons, queries, reservations, rsv_report, business_register,qry_report
# Register your models here.
admin.site.register(business_register)
admin.site.register(establishments)
admin.site.register(patrons)
admin.site.register(queries)
admin.site.register(reservations)
admin.site.register(rsv_report)
admin.site.register(qry_report)