from django import forms
from .models import TRANSACTION_MODES, CurrentForm, Company, PlayerStats

# We need to get a dictionary of player ids and player names here to avoid the possibility of confusion in case there are 2 players with the same name.

# players = [tuple([x,y]) for x,y in <something that contains the player names and ids>]
player_names = [(1,'Pranay Karwa'), (2,'Komal Sharma'), (3,'Anayra Karwa')]
team_names = [(1, 'Mumbai Indians'),(2, 'Chennai Super Kings'),(3, 'Kolkata Knight Riders')]
runs_options = [tuple([x,x]) for x in range(0,8)]
extra_types = [(0, 'none'),(1, 'wides'),(2,'no-ball'),(3,'byes'),(4,'legbyes')]
dismissal_types = [(0,'none'),(1, 'caught'),(2,'bowled'),(3,'lbw'),(4,'runout'),(5,'retired hurt')]

class CompanyChangeForm(forms.Form):
    price = forms.CharField(required=True, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'pattern': '[0-9]+',
        'title': 'Enter integers only',
        'placeholder': 'Enter positive integers only'
    }))

class ScoreCardForm(forms.Form):
    batsman = forms.ChoiceField(label='Batsman', choices=player_names)
    bowler = forms.ChoiceField(label='Bowler', choices=player_names)
    nonstriker = forms.ChoiceField(label='Non-striker', choices=player_names)
    runs_batsman = forms.ChoiceField(label='Batsman runs', choices=runs_options)
    runs_extra = forms.ChoiceField(label='Extras', choices=runs_options)
    extra_type = forms.ChoiceField(label='Extra type', choices=extra_types)
    dismissal_type = forms.ChoiceField(label='Mode of dimsissal (if wicket has fallen)', choices=dismissal_types)
    dismissed_batsman = forms.ChoiceField(label='Batsman dismissed (if wicket has fallen)', choices=player_names)
    fielder = forms.ChoiceField(label='Fielder/Wicketkeeper (only for catches, stumpings, runouts)', choices=player_names)

class MatchCreationForm(forms.Form):
    match_id = forms.IntegerField()
    home_team = forms.ChoiceField(label='Home team', choices=team_names)
    away_team = forms.ChoiceField(label='Away team', choices=team_names)
    home_team_player_names = forms.ChoiceField(label='Home team players', choices=player_names) # This needs to be a dependent drop down based on the home_team
    away_team_player_names = forms.ChoiceField(label='Away team players', choices=player_names) # This needs to be a dependent drop down based on the away_team
    #home_team_player_names = forms.ModelMultipleChoiceField(widget=forms.CheckboxSelectMultiple, queryset=PlayerStats.objects.filter(ipl_team = home_team))
    #away_team_player_names = forms.ModelMultipleChoiceField(widget=forms.CheckboxSelectMultiple, queryset=PlayerStats.objects.filter(ipl_team = away_team))
    batting_team = forms.ChoiceField(label='Batting team', choices=team_names)