# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from .utils import get_job, set_job_status
import numpy as np
import time

example_text = """There's little can be said in 't; 'tis against the
rule of nature. To speak on the part of virginity,
is to accuse your mothers; which is most infallible
disobedience. He that hangs himself is a virgin:
virginity murders itself and should be buried in
highways out of all sanctified limit, as a desperate
offendress against nature. Virginity breeds mites,
much like a cheese; consumes itself to the very
paring, and so dies with feeding his own stomach.
Besides, virginity is peevish, proud, idle, made of
self-love, which is the most inhibited sin in the
canon. Keep it not; you cannot choose but loose
by't: out with 't! within ten year it will make
itself ten, which is a goodly increase; and the
principal itself not much the worse: away with 't!""".split("\n")


class InvalidJob(Exception):
    pass


class JobDispatch(object):
    """Super-ghetto asynchronous jobs framework: Return a web page, which then makes another request(s) to start asynchronous jobs."""
    def __call__(self, job, **kwargs):
        if kwargs.get("name") == "progress-test":
            return progress_test(job, **kwargs)
        if kwargs.get("name") == "hist-test":
            return hist_data(job, **kwargs)
        else:
            raise InvalidJob


def progress_test(job, **kwargs):
    time.sleep(0.5)
    set_job_status(kwargs["status"], {"status": "Dispatched..."})
    for x in example_text:
        time.sleep(0.5)
        set_job_status(kwargs["status"], {"status": x})
    set_job_status(kwargs["status"], {"status": "Finished", "finished": True})
    return "done"


def hist_data(job, **kwargs):
    data = np.random.normal(size=100)
    while data.shape[0] < 1e5:
        data = np.hstack((data, np.random.normal(size=100)))
        # data.sort()
        # data = data[5:-5]
        nbins = min(max(int(data.shape[0] ** 0.5), 10), 50)
        hist, bins = np.histogram(data, bins=nbins)
        xs = ((bins[:-1] + bins[1:]) / 2).tolist()
        ys = hist.tolist()
        set_job_status(kwargs["status"], {"data": [{"x": x, "y": y} for x, y \
            in zip(xs, ys)], "status": "working"})
        time.sleep(0.1)
    set_job_status(kwargs["status"], {"status": "finished",
        "data": [{"x": x, "y": y} for x, y in zip(xs, ys)]})
    return "done"
