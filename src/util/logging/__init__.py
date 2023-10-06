import traceback

from src.util import aws


def log_exceptions(func):
    def run(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except BaseException:
            traceback.print_exc()
            exception = traceback.format_exc()
            message = f"Exception encountered during {__name__}" \
                      f"::{func.__name__}\n\n\n{exception}"
            aws.post_exception_to_sns(message)

    return run
