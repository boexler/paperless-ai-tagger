import logging

from cursor_sdk import Cursor, CursorAgentError

logger = logging.getLogger(__name__)


def _format_parameter_values(parameter: object) -> str:
    """Format allowed parameter values for log output."""
    values = getattr(parameter, "values", None) or []
    parts: list[str] = []
    for value in values:
        raw = getattr(value, "value", value)
        display = getattr(value, "display_name", None)
        parts.append(f"{raw} ({display})" if display else str(raw))
    return ", ".join(parts) if parts else "—"


def _format_variant_params(variant: object) -> str:
    """Format variant parameter overrides for log output."""
    params = getattr(variant, "params", None) or []
    if not params:
        return "—"
    return ", ".join(
        f"{getattr(param, 'id', '?')}={getattr(param, 'value', '?')}" for param in params
    )


def _log_model(model: object) -> None:
    """Log one model entry with parameters and variants."""
    model_id = getattr(model, "id", "?")
    display_name = getattr(model, "display_name", None) or model_id
    description = getattr(model, "description", None)
    aliases = getattr(model, "aliases", None) or []

    header = f"  {model_id} ({display_name})"
    if description:
        header = f"{header} — {description}"
    logger.info(header)

    if aliases:
        logger.info("    aliases: %s", ", ".join(str(alias) for alias in aliases))

    parameters = getattr(model, "parameters", None) or []
    if parameters:
        logger.info("    parameters:")
        for parameter in parameters:
            param_id = getattr(parameter, "id", "?")
            param_name = getattr(parameter, "display_name", None) or param_id
            logger.info(
                "      %s: %s [%s]",
                param_id,
                param_name,
                _format_parameter_values(parameter),
            )

    variants = getattr(model, "variants", None) or []
    if variants:
        logger.info("    variants:")
        for variant in variants:
            variant_name = getattr(variant, "display_name", None) or "unnamed"
            default_suffix = " (default)" if getattr(variant, "is_default", False) else ""
            variant_description = getattr(variant, "description", None)
            line = f"      {variant_name}{default_suffix}: {_format_variant_params(variant)}"
            if variant_description:
                line = f"{line} — {variant_description}"
            logger.info(line)


def log_available_cursor_models(api_key: str) -> None:
    """Fetch and log all Cursor models available to the configured API key."""
    try:
        models = Cursor.models.list(api_key=api_key)
    except CursorAgentError as exc:
        logger.warning("Failed to list Cursor models at startup: %s", exc)
        return
    except Exception as exc:
        logger.warning("Failed to list Cursor models at startup: %s", exc)
        return

    logger.info("Cursor models (%s available):", len(models))
    for model in models:
        _log_model(model)
