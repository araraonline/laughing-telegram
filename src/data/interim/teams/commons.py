import re

from src.util import re_strip


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

        # cache placeholder
        self._fname_without_state = None

    @property
    def fname_without_state(self):
        if self.state is None:
            return self.fname

        if self._fname_without_state is None:
            pattern = r'\b{}\b'
            pattern = pattern.format(re.escape(self.state))
            fname_without_state = re.sub(pattern, '', self.fname)
            fname_without_state = re_strip(fname_without_state)
            self._fname_without_state = fname_without_state
            return fname_without_state

        return self._fname_without_state

    def __str__(self):
        return self.string

    def __repr__(self):
        return 'Team ("{}")'.format(self.string)
