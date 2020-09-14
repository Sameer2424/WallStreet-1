from django.conf.urls import url
from django.urls import path
from .views import (
    MarketOverview,
    CompanyTransactionView,
    CompanyCMPChartData,
    CompanyAdminCompanyUpdateView,
    deduct_tax,
    UpdateMarketView,
    DashboardView,
    MatchCreationView
)

from . import views

app_name = 'Market'


urlpatterns = [
    #path("dashboard", views.dashboard, name = "dashboard"),
    path("executetrades", views.executetrades, name = "executetrades"),
    url(r'^match/', MatchCreationView.as_view(), name='match'),
    url(r'^dashboard/', DashboardView.as_view(), name='dashboard'),
    url(r'^overview/$', MarketOverview.as_view(), name='overview'),
    url(r'^transact/(?P<code>\w+)$', CompanyTransactionView.as_view(), name='transaction'),
    url(r'^admin/(?P<code>\w+)$', CompanyAdminCompanyUpdateView.as_view(), name='admin'),
    url(r'^company/api/(?P<code>\w+)$', CompanyCMPChartData.as_view(), name='cmp_api_data'),
    url(r'^tax/$', deduct_tax, name='tax'),
    url(r'^update/$', UpdateMarketView.as_view(), name='update')
]