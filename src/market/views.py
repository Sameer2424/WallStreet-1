from datetime import datetime
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.views import View
from django.views.generic import ListView
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.utils import timezone
from django.utils.timezone import localtime
from django.conf import settings
from django.urls import reverse

from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Company, InvestmentRecord, Transaction, CompanyCMPRecord, News, UserNews, TransactionScheduler, Buybook, Sellbook, CompletedOrders, PlayerStats, CurrentMatch, Match
from .forms import CompanyChangeForm, ScoreCardForm, MatchCreationForm
from WallStreet.mixins import LoginRequiredMixin, AdminRequiredMixin, CountNewsMixin
from stocks.models import StocksDatabasePointer

import psycopg2

#For Player Data parsing
import requests
from bs4 import BeautifulSoup
import dateparser

User = get_user_model()

START_TIME = timezone.make_aware(getattr(settings, 'START_TIME'))
STOP_TIME = timezone.make_aware(getattr(settings, 'STOP_TIME'))


@login_required
def deduct_tax(request):
    if request.user.is_superuser:
        for user in User.objects.all():
            tax = user.cash * Decimal(0.4)
            user.cash -= tax
            user.save()
        return HttpResponse('success')
    return redirect('/')

class UpdateMarketView(LoginRequiredMixin, AdminRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        # update cmp
        StocksDatabasePointer.objects.get_pointer().increment_pointer()

        # scheduler
        schedule_qs = TransactionScheduler.objects.all()
        for query in schedule_qs:
            if query.perform_transaction(query.company.cmp):
                TransactionScheduler.objects.get(pk=query.pk).delete()

        return HttpResponse('cmp updated')

# What happens if we define a market overview model?
class MarketOverview(LoginRequiredMixin, CountNewsMixin, ListView):
    template_name = 'market/overview.html'
    queryset = Company.objects.all()
    #queryset = Company.objects.order_by('updated').get() #This is for displaying the list of players on the grey bar above the title MARKET OVERVIEW

    def get_context_data(self, *args, **kwargs):
        context = super(MarketOverview, self).get_context_data(*args, **kwargs)
        context['investments'] = InvestmentRecord.objects.filter(user=self.request.user)
        return context

class CompanyAdminCompanyUpdateView(AdminRequiredMixin, CountNewsMixin, View):
    def get(self, request, *args, **kwargs):
        company = Company.objects.get(code=kwargs.get('code'))
        return render(request, 'market/admin_company_change.html', {
            'object': company,
            'company_list': Company.objects.all(),
            'form': CompanyChangeForm()
        })

    def post(self, request, *args, **kwargs):
        company = Company.objects.get(code=kwargs.get('code'))
        price = request.POST.get('price')
        old_price = company.cmp
        company.cmp = Decimal(int(price))
        company.save()
        company.calculate_change(old_price)
        print('price', int(price))
        url = reverse('market:admin', kwargs={'code': company.code})
        return HttpResponseRedirect(url)


class CompanyTransactionView(LoginRequiredMixin, CountNewsMixin, View):  #This is what is causing Investment Record entry to be created every time the user visits a stock's profile page
    def get(self, request, *args, **kwargs):
        company_code = kwargs.get('code')
        company = Company.objects.get(code=company_code)
        # I tried turning this method to InvestmentRecord.objects.get instead of get_or_create, but apparently, the players' profile pages are getting created based on the InvestmentRecordObject being created here.
        obj, _ = InvestmentRecord.objects.get_or_create(user=request.user, company=company)
        stocks_owned = obj.stocks
        context = {
            'object': company,
            'company_list': Company.objects.all(),
            'stocks_owned': stocks_owned,
            'purchase_modes': ['buy', 'sell']
        }
        return render(request, 'market/transaction_market.html', context)

    def post(self, request, *args, **kwargs):
        """This method handles any post data at this page (primarily for transaction)"""
        company = Company.objects.get(code=kwargs.get('code'))
        current_time = timezone.make_aware(datetime.now())

        if START_TIME <= current_time <= STOP_TIME:
            user = request.user
            quantity = request.POST.get('quantity')

            if quantity != '' and int(quantity) > 0:
                quantity = int(quantity)
                mode = request.POST.get('mode')
                purchase_mode = request.POST.get('p-mode')
                price = company.cmp
                # Investment object is being used only to check if the user has sufficient stock balance before trying to sell
                # When I try to use get, it shows the following error: TypeError: cannot unpack non-iterable InvestmentRecord object
                investment_obj, _ = InvestmentRecord.objects.get_or_create(user=user, company=company)
                holding = investment_obj.stocks
                # If num_stocks for sell orders are stored as negative integers, we could aggregate num_stocks and come to the holding for a particular company - WORKS!
                '''sql = "SELECT stocks as holding FROM MARKET_COMPLETEDORDERS WHERE user_id = " + str(user.id) + " AND COMPANY_ID = " + str(company.id) + " GROUP BY COMPANY_ID;"
                holding = 0
                conn = psycopg2.connect(database="wallstreet", user="postgres", password="admin", host="localhost", port="5432")
                cursor = conn.cursor()
                cursor.execute(sql)
                holdings = [row for row in cursor]
                for entry in holdings:
                    holding = entry[0]'''


                # This code is for when the num_stocks for sell orders are stored as positive integers - WORKS!
                '''holding = 0
                sql = "SELECT num_stocks, mode FROM MARKET_COMPLETEDORDERS WHERE user_id = " + str(user.id) + " AND COMPANY_ID = " + str(company.id) + ";"

                conn = psycopg2.connect(database="wallstreet", user="postgres", password="admin", host="localhost", port="5432")
                cursor = conn.cursor()
                cursor.execute(sql)
                mode_and_qty = [row for row in cursor]
                for entry in mode_and_qty:
                    if entry[1] == 'BUY':
                        holding = holding + entry[0]
                    elif entry[1] == 'SELL':
                        holding = holding - entry[0]'''

                if mode == 'transact':
                    if purchase_mode == 'buy':
                        purchase_amount = Decimal(quantity)*price
                        if user.cash >= purchase_amount:
                            # Creating a buybook object instead of a Transaction object
                            #_ = Buybook.objects.create( 
                            _ = Transaction.objects.create(
                                user=user,
                                company=company,
                                num_stocks=quantity,
                                orderprice=price,
                                mode=purchase_mode.upper()
                                #user_net_worth=InvestmentRecord.objects.calculate_net_worth(user)
                            )
                            # Along with recording the transaction in the order book, we also need to indicate the order qty in the Investment Record table
                            # This was happening in pre_save_transaction_receiver, but stocks are getting added to escrow even if there is an error
                            obj, _ = InvestmentRecord.objects.get_or_create(user=request.user, company=company)
                            obj.buy_escrow = obj.buy_escrow + quantity
                            obj.save()
                            print("buy escrow = " + str(obj.buy_escrow))
                            

                            user.escrow = user.escrow + purchase_amount
                            user.cash = user.cash - purchase_amount
                            user.save()
                            messages.success(request, 'Your buy order for ' + str(quantity) + ' shares of ' + company.name + ' has been placed.')
                        else:
                            messages.error(request, 'You do not have sufficient credits for this transaction.')
                    elif purchase_mode == 'sell':
                        if quantity <= holding:
                            #_ = Sellbook.objects.create( 
                            _ = Transaction.objects.create(
                                user=user,
                                company=company,
                                num_stocks=quantity,
                                orderprice=price,
                                mode=purchase_mode.upper()
                                #user_net_worth=InvestmentRecord.objects.calculate_net_worth(user)
                            )
                            # Along with recording the transaction in the order book, we also need to indicate the order qty in the Investment Record table
                            # This was happening in pre_save_transaction_receiver, but stocks are getting added to escrow even if there is an error
                            obj, _ = InvestmentRecord.objects.get_or_create(user=request.user, company=company)
                            obj.sell_escrow = obj.sell_escrow + quantity
                            obj.stocks = obj.stocks - quantity
                            obj.save()
                            print("sell escrow = " + str(obj.sell_escrow))

                            messages.success(request, 'Your sell order for ' + str(quantity) + ' shares of ' + company.name + ' has been placed.')
                        else:
                            messages.error(request, 'You do not have these many stocks to sell for ' + company.name + '.')
                    else:
                        messages.error(request, 'Please select a valid purchase mode.')
                elif mode == 'schedule':
                    schedule_price = request.POST.get('price')
                    if purchase_mode == 'buy':
                        _ = TransactionScheduler.objects.create(
                            user=user,
                            company=company,
                            num_stocks=quantity,
                            price=schedule_price,
                            mode=purchase_mode
                        )
                        messages.success(request, 'Request Submitted!')
                    elif purchase_mode == 'sell':
                        _ = TransactionScheduler.objects.create(
                            user=user,
                            company=company,
                            num_stocks=quantity,
                            price=schedule_price,
                            mode=purchase_mode
                        )
                        messages.success(request, 'Request Submitted.')
                    else:
                        messages.error(request, 'Please select a valid purchase mode.')
                else:
                    messages.error(request, 'Please select a valid transaction mode.')
            else:
                messages.error(request, 'Please enter a valid quantity.')
        else:
            msg = 'The market is closed!'
            messages.info(request, msg)
        url = reverse('market:transaction', kwargs={'code': company.code})
        if request.is_ajax():
            return JsonResponse({'next_path': url})
        return HttpResponseRedirect(url)


# For Chart
class CompanyCMPChartData(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, format=None, *args, **kwargs):
        '''qs = CompanyCMPRecord.objects.filter(company__code=kwargs.get('code'))
        if qs.count() > 15:
            qs = qs[:15]
        qs = reversed(qs)'''
        labels = []
        cmp_data = []
        '''for cmp_record in qs:
            labels.append(localtime(cmp_record.timestamp).strftime('%H:%M'))
            cmp_data.append(cmp_record.cmp)
        current_cmp = Company.objects.get(code=kwargs.get('code')).cmp
        if cmp_data[-1] != current_cmp: # ???
            labels.append(timezone.make_aware(datetime.now()).strftime('%H:%M'))
            cmp_data.append(current_cmp)
        '''
        data = {
            "labels": labels,
            "cmp_data": cmp_data,
        }
        return Response(data)


class NewsView(LoginRequiredMixin, CountNewsMixin, View):
    template_name = 'market/news.html'
    url = 'news'

    def get(self, request, *args, **kwargs):
        UserNews.objects.get_by_user(request.user).update(read=True)
        queryset = News.objects.filter(is_active=True)
        return render(request, 'market/news.html', {'object_list': queryset})

def executetrades(request):
    sql = 'call execute_trades();'
    conn = psycopg2.connect(database="wallstreet", user="postgres", password="admin", host="localhost", port="5432")
    cursor = conn.cursor()
    cursor.execute(sql)
    conn.commit()
    cursor.close()
    conn.close()
    message = 'Trades successfully executed.'
    return redirect('/', {'executionsuccess':message})

'''def dashboard(request):
    form = ScoreCardForm(request.POST or None, request.FILES or None)
    if request.method == 'POST':
        submitbutton = "Submit"
        form = ScoreCardForm(request.POST or None)
        batsman = ''
        bowler = ''
        nonstriker = ''
        if form.is_valid():
            batsman = form.cleaned_data.get("batsman")
            bowler = form.cleaned_data.get("bowler")
            nonstriker = form.cleaned_data.get("nonstriker")
            print('Batsman is ' + batsman)
            print('Bowler is ' + bowler)
            print('Non-striker is ' + nonstriker)
        context = {'form': form, 'batsman': batsman, 'nonstriker': nonstriker, 'bowler':bowler, 'submitbutton':submitbutton}
        return render(request, 'market/trial.html', context)
    else:
        context = {'form':form}
        return render(request, 'market/dashboard.html')'''


class MatchCreationView(LoginRequiredMixin, CountNewsMixin, View):
    template_name = 'market/match_details.html'
    url = 'match'

    def get(self, request, *args, **kwargs):
        form = MatchCreationForm(request.POST or None, request.FILES or None)
        #UserNews.objects.get_by_user(request.user).update(read=True)
        #queryset = News.objects.filter(is_active=True)
        context = {'form':form}
        return render(request, 'market/match_details.html', context)
    
    def post(self, request, *args, **kwargs):
        # This code will run whenever the submit button is pressed on the Match Creation form.
        # Before displaying the score card dashboard, we need to create 22 entries in the 'Match' table with the players that have been selected in the Match form.
        #submitbutton = request.POST.get("submit")

        form = MatchCreationForm(request.POST or None)
        
        # form = ScoreCardForm(request.POST or None)
        
        # if form.is_valid():
        #     batsman = form.cleaned_data.get("batsman")
        #     bowler = form.cleaned_data.get("bowler")
        #     nonstriker = form.cleaned_data.get("nonstriker")
        #     runs_batsman = form.cleaned_data.get("runs_batsman")
        #     print(batsman)
        #     print(bowler)
        #     print(nonstriker)
        #     print(runs_batsman)
        
        match_id = 0
        home_team = ''
        away_team = ''
        home_team_players=[]
        away_team_players=[]
        
        #form = ScoreCardForm(None) # We need a blank form to start
        if form.is_valid():
            match_id = form.cleaned_data.get("match_id")
            home_team = form.cleaned_data.get("home_team")
            away_team = form.cleaned_data.get("away_team")
            home_team_players = form.cleaned_data.get("home_team_players") # This would be a list of player ids
            away_team_players = form.cleaned_data.get("away_team_players") # This would be a list of player ids
            batting_team = form.cleaned_data.get("batting_team")
            print(match_id)
            print(home_team)
            print(away_team)
            print(home_team_players)
            print(away_team_players)
            print(batting_team)
            # Data has been collected in variables, now pushing them into the db
            conn = psycopg2.connect(database="wallstreet", user="postgres", password="admin", host="localhost", port="5432")
            cursor = conn.cursor()
            sql = "delete from market_currentmatch where match_id <> " + str(match_id) + ";"
            cursor.execute(sql)
            sql = "insert into market_currentmatch (match_id, home_team, away_team, batting_team) values (" + str(match_id) + ", '" + home_team + "', '" + away_team + "', '" + batting_team + "');"
            cursor.execute(sql)

            for home_team_player in home_team_players:
                player = PlayerStats.objects.all().filter(id=int(home_team_player))
                for p in player:
                    print("Player id: " + str(p.id))
                    print("Player name: " + p.name)
                    print("Player team: " + p.ipl_team)
                sql = "insert into market_match (runs, balls_faced, fours, sixes, catches, stumpings, runouts, dismissed, balls_bowled, runs_conceded, wickets, match_id, player_id, name, team) values (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, " + str(match_id) + ", '" + str(p.id) + "', '" + p.name + "', '" + p.ipl_team + "');"
                cursor.execute(sql)

            for away_team_player in away_team_players:
                player = PlayerStats.objects.all().filter(id=int(away_team_player))
                for p in player:
                    print("Player id: " + str(p.id))
                    print("Player name: " + p.name)
                    print("Player team: " + p.ipl_team)
                sql = 'insert into market_match (runs, balls_faced, fours, sixes, catches, stumpings, runouts, dismissed, balls_bowled, runs_conceded, wickets, match_id, player_id, name, team) values (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,' + str(match_id) + ", '" + str(p.id) + "', '" + p.name + "', '" + p.ipl_team + "');"
                cursor.execute(sql)
            
            conn.commit()
            cursor.close()
            conn.close()

            # return redirect('/match/dashboard/?match_id=' + match_id +'&home_team=' + home_team + '&away_team=' + away_team)
        context = {'form':form, 'match_id': match_id, 'home_team':home_team,'away_team':away_team}
        return render(request, 'market/match_details.html', context)


def match_create_view(request):
    pass
    # form = MatchCreationForm()
    # if request.method == 'POST':
    #     form = MatchCreationForm(request.POST)
    #     if form.is_valid():
    #         form.save()
    #         return redirect('match_add')
    # return render(request, 'market/match_details.html', {'form': form})


def match_update_view(request, pk):
    pass
    # match = get_object_or_404(Match, pk=pk)
    # form = MatchCreationForm(instance=match)
    # if request.method == 'POST':
    #     form = MatchCreationForm(request.POST, instance=match)
    #     if form.is_valid():
    #         form.save()
    #         return redirect('match_change', pk=pk)
    # return render(request, 'market/match_details.html', {'form': form})

# AJAX
def load_players(request):
    home_team = request.GET.get('home_team')
    away_team = request.GET.get('away_team')
    home_team_players = PlayerStats.objects.filter(ipl_team=home_team).all()
    away_team_players = PlayerStats.objects.filter(ipl_team=away_team).all()
    return render(request, 'market/player_check_list_options.html', {'home_team_players': home_team_players,'away_team_players':away_team_players})
    # return JsonResponse(list(cities.values('id', 'name')), safe=False)

class DashboardView(LoginRequiredMixin, CountNewsMixin, View):
    template_name = 'market/dashboard.html'
    url = 'dashboard'

    def get(self, request, *args, **kwargs):
        match, _ = CurrentMatch.objects.get_or_create()
        match_id = match.match_id
        home_team = match.home_team
        away_team = match.away_team
        batting_team = match.batting_team
        print(match_id)
        print(home_team)
        print(away_team)
        print(batting_team)
        # current_match = CurrentMatch.objects.all()
        # for match in current_match:
        #     match_id = match.match_id
        #     home_team = match.home_team
        #     away_team = match.away_team
        #     batting_team = match.batting_team
        #     print(match_id)
        #     print(home_team)
        #     print(away_team)
        #     print(batting_team)
        batters = Match.objects.all().filter(team__icontains=batting_team)
        if batting_team == home_team:
            bowling_team = away_team
        else:
            bowling_team = home_team
        print(bowling_team)
        bowlers = Match.objects.all().filter(team__icontains=bowling_team)
        form = ScoreCardForm(request.POST or None, request.FILES or None)
        context = {'form': form, 'batters':batters, 'bowlers':bowlers, 'match_id':match_id, 'home_team':home_team, 'away_team':away_team}
        return render(request, 'market/dashboard.html', context)
    
    def post(self, request, *args, **kwargs):
        current_match = CurrentMatch.objects.all()
        for match in current_match:
            match_id = match.match_id
            home_team = match.home_team
            away_team = match.away_team
            batting_team = match.batting_team

        form = ScoreCardForm(request.POST)
        batsman = 0
        bowler = 0
        nonstriker = 0
        runs_batsman = 0
        runs_extra = 0
        extra_type = 0
        dismissal_type = 0
        dismissed_batsman = 0
        fielder = 0
        if form.is_valid():
            batsman = form.cleaned_data.get("batsman")
            bowler = form.cleaned_data.get("bowler")
            nonstriker = form.cleaned_data.get("nonstriker")
            runs_batsman = form.cleaned_data.get("runs_batsman")
            runs_extra = form.cleaned_data.get("runs_extra")
            extra_type = form.cleaned_data.get("extra_type")
            dismissal_type = form.cleaned_data.get("dismissal_type")
            dismissed_batsman = form.cleaned_data.get("dismissed_batsman")
            fielder = form.cleaned_data.get("fielder")
            print(batsman)
            print(bowler)
            print(nonstriker)
            print(runs_batsman)
            print(runs_extra)
            print(extra_type)
            print(dismissal_type)
            print(dismissed_batsman)
            print(fielder)
        
        batsman, _ = Match.objects.get_or_create(player_id=batsman,match_id=match_id)
        nonstriker, _ = Match.objects.get_or_create(player_id=nonstriker,match_id=match_id)
        bowler, _ = Match.objects.get_or_create(player_id=bowler,match_id=match_id)
        fielder, _ = Match.objects.get_or_create(player_id=fielder,match_id=match_id)
        dismissed_batsman, _ = Match.objects.get_or_create(player_id=dismissed_batsman,match_id=match_id)
        
        batsman.runs = batsman.runs + int(runs_batsman)
        bowler.runs_conceded = bowler.runs_conceded + int(runs_batsman)
        if int(runs_batsman) == 4:
            batsman.fours = batsman.fours + 1
        elif int(runs_batsman) == 6:
            batsman.sixes = batsman.sixes + 1
        
        if int(runs_extra) == 0:
            bowler.balls_bowled = bowler.balls_bowled + 1
            batsman.balls_faced = batsman.balls_faced + 1
        else:
            if int(extra_type) == 1 or int(extra_type) == 2:
                bowler.runs_conceded = bowler.runs_conceded + int(runs_extra)
            elif int(extra_type) == 3 or int(extra_type) == 4:
                bowler.balls_bowled = bowler.balls_bowled + 1
        
        if int(dismissal_type) == 1:
            dismissed_batsman.dismissed = 1
            fielder.catches = fielder.catches + 1
            bowler.wickets = bowler.wickets + 1
        elif int(dismissal_type) == 2:
            dismissed_batsman.dismissed = 1
            bowler.wickets = bowler.wickets + 1
        elif int(dismissal_type) == 3:
            dismissed_batsman.dismissed = 1
            bowler.wickets = bowler.wickets + 1
        elif int(dismissal_type) == 4:
            dismissed_batsman.dismissed = 1
            fielder.runouts = fielder.runouts + 1
        elif int(dismissal_type) == 5:
            dismissed_batsman.dismissed = 1
            fielder.stumpings = fielder.stumpings + 1
            bowler.wickets = bowler.wickets + 1
    
        batsman.save()
        bowler.save()
        nonstriker.save()
        fielder.save()
        dismissed_batsman.save()
        
        #SQL code to be pasted here - pasted in scratchpad.sql in C:\Users\Pranay Karwa\Projects\WallStreet-master
        
        conn = psycopg2.connect(database="wallstreet", user="postgres", password="admin", host="localhost", port="5432")
        cursor = conn.cursor()
        sql = 'call update_valuations(' + str(batsman.player_id) + ');'
        cursor.execute(sql)
        # sql = 'call update_valuations(' + str(nonstriker.player_id) + ');' # No need to call for nonstriker. If he is runout, it'll be taken care of with dismissed_batsman
        # cursor.execute(sql)
        sql = 'call update_valuations(' + str(bowler.player_id) + ');'
        cursor.execute(sql)
        sql = 'call update_valuations(' + str(fielder.player_id) + ');'
        cursor.execute(sql)
        sql = 'call update_valuations(' + str(dismissed_batsman.player_id) + ');'
        cursor.execute(sql)
        conn.commit()
        cursor.close()
        conn.close()

        context = {'form': form, 'match_id':match_id, 'home_team':home_team, 'away_team':away_team}
        #, 'batsman': batsman, 'nonstriker': nonstriker, 'bowler':bowler, 'submitbutton':submitbutton}
        return render(request, 'market/dashboard.html', context)


# Open a connection pool and keep them open.  Whenever the db needs to be hit, you fetch a connection, do whatever you need to, and put it back in the pool.

def search(request):
    query = ''

    query = request.GET['query']
    allCompanies = Company.objects.all().filter(name__icontains=query)
    context = {'allCompanies':allCompanies , 
        'query':query,}
    return render(request,'market/search.html',context)