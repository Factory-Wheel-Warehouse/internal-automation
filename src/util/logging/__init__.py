import traceback

from src.util import aws


def log_exceptions(func):
    def run(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except BaseException:
            traceback.print_exc()
            exception = traceback.format_exc()
            message = f"Exception encountered during {func.__qualname__}" \
                      f"\n\n\n{exception}"
            aws.post_exception_to_sns(message)

    run.__name__ = func.__name__

    return run
