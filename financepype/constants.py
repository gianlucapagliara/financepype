import os
import platform
from decimal import Decimal
from hashlib import md5

s_decimal_0 = Decimal("0")
s_decimal_max = Decimal("1e20")
s_decimal_min = Decimal("1e-20")
s_decimal_inf = Decimal("inf")
s_decimal_NaN = Decimal("NaN")


def get_instance_id() -> str:
    return md5(
        f"{platform.uname()}_pid:{os.getpid()}_ppid:{os.getppid()}".encode()
    ).hexdigest()
