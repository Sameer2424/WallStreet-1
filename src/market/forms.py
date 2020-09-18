from django import forms
from .models import TRANSACTION_MODES, CurrentForm, Company, PlayerStats, ScoreCard, CurrentMatch, Match
#from .views import home, away

# We need to get a dictionary of player ids and player names here to avoid the possibility of confusion in case there are 2 players with the same name.

# players = [tuple([x,y]) for x,y in <something that contains the player names and ids>]
batting_team = ''
bowling_team = ''
currentmatch = CurrentMatch.objects.all()
bowling_team_players = ''
for match in currentmatch:
    batting_team = Match.objects.all().filter(team=match.batting_team)
    if match.home_team == match.batting_team:
        bowling_team = match.away_team
    else:
        bowling_team = match.home_team
    bowling_team_players = Match.objects.all().filter(team=bowling_team)
# Options for choice fields needs to be a LIST of TUPLES
batters = [(0,'None')]
batters = batters + [tuple([player.player_id,player.name]) for player in batting_team ]
bowlers = [(0,'None')]
bowlers = bowlers + [tuple([player.player_id,player.name]) for player in bowling_team_players ]

players = PlayerStats.objects.all()
all_players = [(0,'None')]
all_players = all_players + [tuple([player.id,player.name]) for player in players ]



team_names = [('No team selected','Select team'),('Royal Challengers Bangalore', 'Royal Challengers Bangalore'),('Chennai Super Kings', 'Chennai Super Kings'),('Delhi Capitals', 'Delhi Capitals'),('Kings XI Punjab','Kings XI Punjab'),('Kolkata Knight Riders','Kolkata Knight Riders'),('Mumbai Indians','Mumbai Indians'),('Rajasthan Royals','Rajasthan Royals'),('Sunrisers Hyderabad','Sunrisers Hyderabad')]
runs_options = [tuple([x,x]) for x in range(0,8)]
extra_types = [(0, 'None'),(1, 'wides'),(2,'no-ball'),(3,'byes'),(4,'legbyes')]
dismissal_types = [(0,'None'),(1, 'caught'),(2,'bowled'),(3,'lbw'),(4,'runout'),(5,'retired hurt')]

class CompanyChangeForm(forms.Form):
    price = forms.CharField(required=True, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'pattern': '[0-9]+',
        'title': 'Enter integers only',
        'placeholder': 'Enter positive integers only'
    }))

class ScoreCardForm(forms.Form):
    # class Meta:
    #     model = ScoreCard
    #     fields = ('id','batsman','bowler','nonstriker')
    batsman = forms.ChoiceField(label='Batsman', choices=batters)
    bowler = forms.ChoiceField(label='Bowler', choices=bowlers)
    nonstriker = forms.ChoiceField(label='Non-striker', choices=batters)
    runs_batsman = forms.ChoiceField(label='Batsman runs', choices=runs_options)
    runs_extra = forms.ChoiceField(label='Extras', choices=runs_options)
    extra_type = forms.ChoiceField(label='Extra type', choices=extra_types)
    dismissal_type = forms.ChoiceField(label='Mode of dimsissal (if wicket has fallen)', choices=dismissal_types)
    dismissed_batsman = forms.ChoiceField(label='Batsman dismissed (if wicket has fallen)', choices=batters)
    fielder = forms.ChoiceField(label='Fielder/Wicketkeeper (only for catches, stumpings, runouts)', choices=bowlers)

class MatchCreationForm(forms.Form):
    match_id = forms.IntegerField()
    home_team = forms.ChoiceField(label='Home team', choices=team_names)
    away_team = forms.ChoiceField(label='Away team', choices=team_names)
    home_team_players = forms.MultipleChoiceField(label='Home team players', widget=forms.CheckboxSelectMultiple, choices=all_players) # This needs to be a dependent drop down based on the home_team
    away_team_players = forms.MultipleChoiceField(label='Away team players', widget=forms.CheckboxSelectMultiple, choices=all_players) # This needs to be a dependent drop down based on the away_team
    #home_team_player_names = forms.ModelMultipleChoiceField(widget=forms.CheckboxSelectMultiple, queryset=PlayerStats.objects.filter(ipl_team = home_team))
    #away_team_player_names = forms.ModelMultipleChoiceField(widget=forms.CheckboxSelectMultiple, queryset=PlayerStats.objects.filter(ipl_team = away_team))
    batting_team = forms.ChoiceField(label='Batting team', choices=team_names)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['home_team_players'].queryset = PlayerStats.objects.none()
        self.fields['away_team_players'].queryset = PlayerStats.objects.none()

        if 'home_team' in self.data:
            try:
                team_name = self.data.get('home_team')
                self.fields['home_team_players'].queryset = PlayerStats.objects.filter(ipl_team=team_name).order_by('name')
            except (ValueError,TypeError):
                pass
        else:
            self.fields['home_team_players'].queryset = PlayerStats.objects.filter().order_by('ipl_team')

        if 'away_team' in self.data:
            try:
                team_name = self.data.get('away_team')
                self.fields['away_team_players'].queryset = PlayerStats.objects.filter(ipl_team=team_name).order_by('name')
            except (ValueError,TypeError):
                pass
        else:
            self.fields['away_team_players'].queryset = PlayerStats.objects.filter().order_by('ipl_team')