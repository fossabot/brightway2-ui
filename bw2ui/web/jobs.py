from utils import get_job, set_job_status
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


class InvalidJob(StandardError):
    pass


class JobDispatch(object):
    """Super-ghetto asynchronous jobs framework: Return a web page, which then makes another request(s) to start asynchronous jobs."""
    def __call__(self, job, **kwargs):
        if kwargs.get("name", None) == "progress-test":
            return progress_test(job, **kwargs)
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
