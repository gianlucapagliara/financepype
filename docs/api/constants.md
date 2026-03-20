# API Reference — Constants

## financepype.constants

Pre-defined `Decimal` constants used throughout the library to avoid repeated object creation and ensure consistent representation of common values.

### Decimal Constants

| Name | Value | Description |
|------|-------|-------------|
| `s_decimal_0` | `Decimal("0")` | Zero |
| `s_decimal_max` | `Decimal("1e20")` | Maximum order size / notional default |
| `s_decimal_min` | `Decimal("1e-20")` | Minimum increment default |
| `s_decimal_inf` | `Decimal("inf")` | Infinity (used in ratio calculations) |
| `s_decimal_NaN` | `Decimal("NaN")` | Not-a-number sentinel |

### Functions

#### get_instance_id

```python
def get_instance_id() -> str
```

Returns an MD5 hash derived from the current machine's `platform.uname()`, the process ID (`os.getpid()`), and the parent process ID (`os.getppid()`).

Used internally by `Operator` to create a unique `_client_instance_id` per running process, enabling identification of which process submitted an operation when multiple processes share the same exchange credentials.

**Example**

```python
from financepype.constants import get_instance_id

instance_id = get_instance_id()
print(instance_id)  # e.g., "a3f2c8d1e4b57690f1234567890abcde"
```

**Returns**: `str` — 32-character hex string

**Note**: The hash changes if the process is restarted (new PID) or if the machine differs. It does not change during the lifetime of a single process.
