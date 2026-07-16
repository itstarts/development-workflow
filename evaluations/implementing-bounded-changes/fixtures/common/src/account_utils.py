"""Small public account utilities used by the evaluation fixture."""


def format_display_name(first_name: str, last_name: str) -> str:
    return f"{first_name} {last_name}"


def retry_delay(attempt: int) -> int:
    return min(2**attempt, 60)


def legacy_banner() -> str:
    return "new banner"
