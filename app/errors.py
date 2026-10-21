"""Custom exceptions. Each carries a short, safe message meant for the user."""


class AppError(Exception):
    """Base class for all expected, user-presentable errors."""

    def __init__(self, user_message: str, details: list[str] | None = None) -> None:
        super().__init__(user_message)
        self.user_message = user_message
        self.details = details or []


class InputError(AppError):
    """The document text, file, or document type is not acceptable."""


class ConfigError(AppError):
    """Configuration (for example the API key) is missing or unusable."""


class LLMError(AppError):
    """The AI provider could not be reached or returned an error."""


class ResponseFormatError(AppError):
    """The AI response was not valid JSON (or not a JSON object)."""


class SchemaValidationError(AppError):
    """The JSON was valid but did not match the Pydantic schema."""
