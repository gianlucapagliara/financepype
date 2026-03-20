# API Reference — Trading Rules

## financepype.rules.trading_rule

### TradingRule

```
class TradingRule(BaseModel)
```

Exchange constraints for a single trading pair.

**Fields**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `trading_pair` | `TradingPair` | required | The pair these rules cover |
| `min_order_size` | `Decimal` | `0` | Minimum base size |
| `max_order_size` | `Decimal` | `1e20` | Maximum base size |
| `min_price_increment` | `Decimal` | `1e-20` | Tick size |
| `min_price_significance` | `int` | `0` | Significant price digits |
| `min_base_amount_increment` | `Decimal` | `1e-20` | Base size step |
| `min_quote_amount_increment` | `Decimal` | `1e-20` | Quote size step |
| `min_notional_size` | `Decimal` | `0` | Minimum order value |
| `max_notional_size` | `Decimal` | `1e20` | Maximum order value |
| `supported_order_types` | `set[OrderType]` | `{LIMIT, MARKET}` | Allowed order types |
| `supported_order_modifiers` | `set[OrderModifier]` | `{POST_ONLY}` | Allowed modifiers |
| `buy_order_collateral_token` | `str \| None` | quote currency | Collateral for buys |
| `sell_order_collateral_token` | `str \| None` | base currency | Collateral for sells |
| `product_id` | `str \| None` | `None` | Exchange product ID |
| `is_live` | `bool` | `True` | Trading enabled |
| `other_rules` | `dict[str, Any]` | `{}` | Extra rules |

**Validators**

- `validate_trading_pair` — accepts `str`, `dict`, or `TradingPair`
- `fix_collateral_tokens` — sets collateral defaults from base/quote

**Properties**

| Property | Type | Description |
|----------|------|-------------|
| `active` | `bool` | `is_active()` with no timestamp |
| `started` | `bool` | `is_started()` with no timestamp |
| `expired` | `bool` | `is_expired()` with no timestamp |
| `supports_limit_orders` | `bool` | `LIMIT in supported_order_types` |
| `supports_market_orders` | `bool` | `MARKET in supported_order_types` |

**Methods**

| Method | Signature | Description |
|--------|-----------|-------------|
| `is_expired` | `(timestamp?) -> bool` | Always `False` for spot |
| `is_started` | `(timestamp?) -> bool` | Always `True` for spot |
| `is_active` | `(timestamp?) -> bool` | Always `True` for spot |

**Decimal Serialization**

Size and price fields serialize to `str` when `.model_dump()` is called, preserving precision.

---

### DerivativeTradingRule

```
class DerivativeTradingRule(TradingRule)
```

Extends `TradingRule` for futures, perpetuals, and options.

**Additional Fields**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `underlying` | `str \| None` | `None` | Underlying asset symbol |
| `strike_price` | `Decimal \| None` | `None` | Strike price for options |
| `start_timestamp` | `float` | `0` | Trading start time |
| `expiry_timestamp` | `float` | `-1` | Trading end time (−1 = perpetual) |
| `index_symbol` | `str \| None` | `None` | Index being tracked |

**Properties**

- `perpetual -> bool` — True when `expiry_timestamp == -1`

**Overridden Methods**

| Method | Signature | Description |
|--------|-----------|-------------|
| `is_expired` | `(timestamp?) -> bool` | True if past `expiry_timestamp` |
| `is_started` | `(timestamp?) -> bool` | True if past `start_timestamp` |
| `is_active` | `(timestamp?) -> bool` | `is_live and is_started and not is_expired` |

**Collateral Defaults** (override from `TradingRule`):

- Linear derivatives: both buy and sell use **quote** as collateral
- Inverse derivatives: both buy and sell use **base** as collateral

---

## financepype.rules.trading_rules_tracker

### TradingRulesTracker

```
class TradingRulesTracker [abstract]
```

Manages a live collection of trading rules and a bidirectional symbol map for one exchange.

**Constructor**

```python
TradingRulesTracker()
```

Creates empty `_trading_rules` dict, `_trading_pair_symbol_map` bidict, and `_mapping_initialization_lock`.

**Properties**

| Property | Type | Description |
|----------|------|-------------|
| `trading_rules` | `dict[TradingPair, TradingRule]` | Current rules |
| `is_locked` | `bool` | True while updating |
| `is_ready` | `bool` | True if map is non-empty |

**Async Methods**

| Method | Signature | Description |
|--------|-----------|-------------|
| `trading_pair_symbol_map` | `async () -> bidict[TradingPair, str]` | Get map, triggering update if needed |
| `all_trading_pairs` | `async () -> list[TradingPair]` | All standard pairs |
| `all_exchange_symbols` | `async () -> list[str]` | All exchange symbols |
| `exchange_symbol_associated_to_pair` | `async (pair) -> str` | Standard → exchange |
| `trading_pair_associated_to_exchange_symbol` | `async (symbol) -> TradingPair` | Exchange → standard |
| `is_trading_pair_valid` | `async (pair) -> bool` | Is pair in map? |
| `is_exchange_symbol_valid` | `async (symbol) -> bool` | Is symbol in map? |
| `update_trading_rules` | `async () -> None` [abstract] | Fetch from exchange |
| `update_loop` | `async (interval_seconds) -> None` | Background update loop |

**Sync Methods**

| Method | Signature | Description |
|--------|-----------|-------------|
| `trading_pair_symbol_map_ready` | `() -> bool` | Map non-empty? |
| `set_trading_pair_symbol_map` | `(map: bidict) -> None` | Replace map |
| `set_trading_rules` | `(rules: dict) -> None` | Replace all rules |
| `set_trading_rule` | `(pair, rule) -> None` | Add/update one rule |
| `remove_trading_rule` | `(pair) -> None` | Remove one rule |

**`update_loop` behaviour**

Calls `update_trading_rules()` in a `while True` loop. On `NotImplementedError` or `CancelledError`, re-raises. On other exceptions, logs and sleeps 0.5 s.
