import logging


class CustomFormatter(logging.Formatter):
    grey = "\x1b[38;20m"
    blue = "\x1b[38;5;39m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"

    _fmt = "%(asctime)s.%(msecs)03d - %(levelname)-8s - %(message)s (%(filename)s:%(lineno)d)"

    FORMATS = {
        logging.DEBUG: grey + _fmt + reset,
        logging.INFO: blue + _fmt + reset,
        logging.WARNING: yellow + _fmt + reset,
        logging.ERROR: red + _fmt + reset,
        logging.CRITICAL: bold_red + _fmt + reset,
    }

    def format(self, record: logging.LogRecord) -> str:
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)


def get_logger(name: str = "football_predictor") -> logging.Logger:
    logger = logging.getLogger(name)

    if logger.handlers:
        # Already configured — avoid adding duplicate handlers if called twice
        return logger

    logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(CustomFormatter())

    logger.addHandler(ch)
    logger.propagate = False

    return logger
