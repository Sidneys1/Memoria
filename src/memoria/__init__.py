from .__about__ import *

from logging import getLogger


MODULE_LOGGER = getLogger(__spec__.name)
MODULE_LOGGER.propagate = True
