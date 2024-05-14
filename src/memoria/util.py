import logging
from collections import UserString

_CSI = "\033[%sm"
RESET = _CSI % 0
"""Special case: NOT a `ColorStr`."""


class ColorStr(UserString):
    _reset: str = RESET

    def __call__(self, content, reset=None) -> str:
        return self.data + str(content) + (reset if reset is not None else self._reset)


def _csi(*nums: int, reset=0) -> ColorStr:
    val = ';'.join(str(num) for num in nums)
    ret = ColorStr(_CSI % val)
    if reset != 0:
        ret._reset = _CSI % str(reset)  # pylint: disable=protected-access
    return ret


BOLD = _csi(1, reset=22)
DIM = _csi(2, reset=22)
ITALIC_OR_REVERSE = _csi(3)
UNDERLINE = _csi(4, reset=24)
BLINK = _csi(5, reset=25)
# FAST_BLINK = _csi(6)  # Disabled, largely redundant
REVERSE = _csi(7, reset=27)
CONCEAL = _csi(8, reset=28)
STRIKE = _csi(9, reset=29)
DEFAULT_COLOR = _csi(39)

RED = _csi(31)
BOLD_RED = _csi(1, 31)

GREEN = _csi(32)
BOLD_GREEN = _csi(1, 32)

YELLOW = _csi(33)
BOLD_YELLOW = _csi(1, 33)

BLUE = _csi(34)
BOLD_BLUE = _csi(1, 34)

MAGENTA = _csi(35)
BOLD_MAGENTA = _csi(1, 35)

CYAN = _csi(36)
BOLD_CYAN = _csi(1, 36)

GREY = _csi(37)
DARK_GREY = _csi(2, 37)
WHITE = _csi(1, 37)

ORANGE = _csi(38, 5, 214)
BOLD_ORANGE = _csi(1, 38, 5, 214)

MONOKAI_STRING = _csi(38, 2, 230, 219, 116)

class ColorFormatter(logging.Formatter):
    _format = "\r%(levelname)8s %(asctime)s %(name)18s │ %(message)s"

    FORMATS = {
        logging.DEBUG: str(DARK_GREY + _format + RESET),
        logging.INFO: str(GREY + _format + RESET),
        logging.WARNING: str(YELLOW + _format + RESET),
        logging.ERROR: str(RED + _format + RESET),
        logging.CRITICAL: str(BOLD_RED + _format + RESET)
    }

    __FORMATTERS: dict[int, logging.Formatter] = {}

    def format(self, record):  # type: ignore
        if record.levelno not in self.__FORMATTERS:
            self.__FORMATTERS[record.levelno] = logging.Formatter(self.FORMATS.get(record.levelno), '%H:%M:%S')
        return self.__FORMATTERS[record.levelno].format(record)


__all__ = [
    'ColorStr',
    'RESET',
    'BOLD',
    'DIM',
    'ITALIC_OR_REVERSE',
    'UNDERLINE',
    'BLINK',
    'REVERSE',
    'CONCEAL',
    'STRIKE',
    'RED',
    'BOLD_RED',
    'GREEN',
    'BOLD_GREEN',
    'YELLOW',
    'BOLD_YELLOW',
    'BLUE',
    'BOLD_BLUE',
    'MAGENTA',
    'BOLD_MAGENTA',
    'CYAN',
    'BOLD_CYAN',
    'GREY',
    'DARK_GREY',
    'WHITE',
    'ORANGE',
    'BOLD_ORANGE',
    'DEFAULT_COLOR'
]
