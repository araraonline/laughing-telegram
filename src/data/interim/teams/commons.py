class Team(object):
    """A Team object

    Represents a team either from loteca or from BetExplorer.
    """
    def __init__(self, string, name, fname, 
                 am_flag=False, women_flag=False,
                 country=None, state=None, under=None):
        assert isinstance(string, str)
        assert isinstance(name, str)
        assert isinstance(fname, str)

        assert isinstance(am_flag, bool)
        assert isinstance(women_flag, bool)

        if country is not None:
            assert isinstance(country, str)
            assert len(country) == 3
            country = country.upper()

        if state is not None:
            assert isinstance(state, str)
            assert len(state) == 2
            state = state.upper()

        if under is not None:
            assert isinstance(under, int)
            assert 0 <= under <= 25

        # set values
        self.string = string
        self.name = name
        self.fname = fname
        self.am_flag = am_flag
        self.women_flag = women_flag
        self.country = country
        self.state = state
        self.under = under

    def __str__(self):
        return self.string

    def __repr__(self):
        return 'Team ("{}")'.format(self.string)

    @classmethod
    def from_another(cls, team, **kwargs):
        return cls(
            kwargs.get('string', team.string),
            kwargs.get('name', team.name),
            kwargs.get('fname', team.fname),
            am_flag    = kwargs.get('am_flag', team.am_flag),
            women_flag = kwargs.get('women_flag', team.women_flag),
            country    = kwargs.get('country', team.country),
            state      = kwargs.get('state', team.state),
            under      = kwargs.get('under', team.under),
        )
