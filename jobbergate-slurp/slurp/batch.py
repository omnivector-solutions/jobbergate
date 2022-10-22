from itertools import islice, chain


def batch(iterable, size):
    """
    Copied from https://code.activestate.com/recipes/303279-getting-items-in-batches/
    """
    sourceiter = iter(iterable)
    while True:
        batchiter = islice(sourceiter, size)
        try:
            yield chain([next(batchiter)], batchiter)
        except StopIteration:
            break
