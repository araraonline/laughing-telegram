import json
import pickle
import re


def load_json(filepath):
    with open(filepath, mode='rb') as f:
        return json.load(f)


def save_json(filepath, obj):
    with open(filepath, mode='wb') as f:
        json.dump(obj, f)


def load_pickle(filepath):
    with open(filepath, mode='rb') as f:
        return pickle.load(f)


def save_pickle(filepath, obj):
    with open(filepath, mode='wb') as f:
        pickle.dump(obj, f)


def re_strip(string):
    """Strips the string using regular expressions

    Args:
        string: the string to be stripped

    Returns:
        A new string, without any leading or trailing non-word characters.
    """
    return re.search(r'^\W*(.*?)\W*$', string).group(1)
