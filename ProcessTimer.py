from collections.abc import Callable
import logging
from time import time

import humanize

def MeasureExecutionTime(StageName: str) -> Callable:
    def Decorator(Function: Callable) -> Callable:
        def Wrapper(*args, **kwargs):
            StartTime = time()
            Result = Function(*args, **kwargs)
            EndTime = time()
            logging.info(f"{StageName}耗时：{humanize.naturaldelta(EndTime - StartTime)}")
            return Result
        return Wrapper
    return Decorator
