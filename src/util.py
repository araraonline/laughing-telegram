import pickle


def save_pickle(filepath, obj):
    with open(filepath, mode='wb') as f:
        pickle.dump(obj, f)


def load_pickle(filepath):
    with open(filepath, mode='rb') as f:
        return pickle.load(f)
