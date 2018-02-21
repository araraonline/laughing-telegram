import re


def re_strip(string):
    """Strips the string using regular expressions

    Args:
        string: the string to be stripped

    Returns:
        A new string, without any leading or trailing non-word characters.
    """
    return re.search(r'^\W*(.*?)\W*$', string).group(1)
