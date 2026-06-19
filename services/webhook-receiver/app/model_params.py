from cursor_sdk import ModelParameterValue, ModelSelection


def parse_cursor_model_params(raw: str) -> list[ModelParameterValue]:
    """Parse CURSOR_MODEL_PARAMS entries in key:value,key:value format."""
    stripped = raw.strip()
    if not stripped:
        return []

    params: list[ModelParameterValue] = []
    for entry in stripped.split(","):
        item = entry.strip()
        if not item:
            continue
        if ":" not in item:
            raise ValueError(
                f"Invalid CURSOR_MODEL_PARAMS entry {item!r}: expected format key:value",
            )
        key, _, value = item.partition(":")
        key = key.strip()
        value = value.strip()
        if not key:
            raise ValueError(
                f"Invalid CURSOR_MODEL_PARAMS entry {item!r}: key must not be empty",
            )
        params.append(ModelParameterValue(id=key, value=value))
    return params


def build_cursor_model_selection(model_id: str, params_raw: str) -> str | ModelSelection:
    """Build a Cursor SDK model selection from model id and raw parameter string."""
    params = parse_cursor_model_params(params_raw)
    if not params:
        return model_id
    return ModelSelection(id=model_id, params=params)


def format_cursor_model_selection(model_id: str, params_raw: str) -> str:
    """Format model id and parameters for startup logging."""
    params = parse_cursor_model_params(params_raw)
    if not params:
        return model_id
    param_text = ",".join(f"{param.id}={param.value}" for param in params)
    return f"{model_id} params={param_text}"
