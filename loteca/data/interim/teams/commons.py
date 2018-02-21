from collections import namedtuple


Team = namedtuple('Team', 'fname, name, string, tokens')

class Tokens(namedtuple('Tokens', 'state, country, am, under, women')):
    def __init__(self, *args, **kwargs):
        self.check_values()
        
    def check_values(self):
        if self.state is not None:
            assert self.state.islower()
            assert len(self.state) == 2

        if self.country is not None:
            assert self.country.islower()
            assert len(self.country) == 3

        assert isinstance(self.am, bool)
        assert isinstance(self.women, bool)

        assert isinstance(self.under, int)
        assert 0 <= self.under <= 25
