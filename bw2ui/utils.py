from pprint import pformat


def terminal_format(data):
    print pformat(data).replace('u"', '"').replace("u'", "'")


def clean_jobs_directory():
    # TODO
    pass
