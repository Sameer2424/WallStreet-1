from django.contrib import admin
from .models import Company, InvestmentRecord, CompanyCMPRecord, Transaction, News, UserNews, TransactionScheduler, Buybook, Sellbook, Buystage, Sellstage


class CompanyAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'code', 'cmp', 'mkt_qty', 'cap')
    search_fields = ('code', 'name')
    ordering = ('id', 'name')

    class Meta:
        model = Company

admin.site.register(Company, CompanyAdmin)


class InvestmentRecordAdmin(admin.ModelAdmin):
    list_display = ('user', 'company', 'stocks')
    search_fields = ['user', 'company']
    ordering = ('user', 'company')

    class Meta:
        model = InvestmentRecord

admin.site.register(InvestmentRecord, InvestmentRecordAdmin)


class CompanyCMPRecordAdmin(admin.ModelAdmin):
    list_display = ('company', 'cmp', 'timestamp')
    search_fields = ['company']
    ordering = ('company', 'timestamp')

    class Meta:
        model = CompanyCMPRecord

admin.site.register(CompanyCMPRecord, CompanyCMPRecordAdmin)


class TransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'company', 'num_stocks', 'price', 'mode', 'timestamp')
    search_fields = ['user', 'company']
    ordering = ('user', 'company', 'mode', 'timestamp')

    class Meta:
        model = Transaction

admin.site.register(Transaction, TransactionAdmin)

# Registering Buybook, Sellbook, Buystage, Sellstage - Pranay

class BuybookAdmin(admin.ModelAdmin):
    list_display = ('user', 'company', 'num_stocks', 'timestamp')
    search_fields = ['user', 'company']
    ordering = ('user', 'company', 'timestamp')

    class Meta:
        model = Transaction

admin.site.register(Buybook, BuybookAdmin)

class SellbookAdmin(admin.ModelAdmin):
    list_display = ('user', 'company', 'num_stocks', 'timestamp')
    search_fields = ['user', 'company']
    ordering = ('user', 'company', 'timestamp')

    class Meta:
        model = Transaction

admin.site.register(Sellbook, SellbookAdmin)

class BuystageAdmin(admin.ModelAdmin):
    list_display = ('user', 'company', 'num_stocks', 'timestamp')
    search_fields = ['user', 'company']
    ordering = ('user', 'company', 'timestamp')

    class Meta:
        model = Transaction

admin.site.register(Buystage, BuystageAdmin)

class SellstageAdmin(admin.ModelAdmin):
    list_display = ('user', 'company', 'num_stocks', 'timestamp')
    search_fields = ['user', 'company']
    ordering = ('user', 'company', 'timestamp')

    class Meta:
        model = Transaction

admin.site.register(Sellstage, SellstageAdmin)

# /Pranay

class NewsAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active')
    search_fields = ['title']
    ordering = ('title', 'is_active')

    class Meta:
        model = News

admin.site.register(News, NewsAdmin)


class UserNewsAdmin(admin.ModelAdmin):
    list_display = ('user', 'news', 'read')
    search_fields = ['user', 'news']
    ordering = ('user', 'news', 'read')

    class Meta:
        model = UserNews

admin.site.register(UserNews, UserNewsAdmin)


class TransactionSchedulerAdmin(admin.ModelAdmin):
    list_display = ('user', 'company', 'num_stocks', 'price', 'mode', 'timestamp')
    search_fields = ['user', 'company', 'mode']
    ordering = ('user', 'company', 'mode', 'price', 'timestamp')

    class Meta:
        model = TransactionScheduler

admin.site.register(TransactionScheduler, TransactionSchedulerAdmin)