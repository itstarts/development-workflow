# Account utilities

`format_display_name(first_name, last_name)` joins both names with one space. The empty-last-name example currently returns `"Ada "`.

`retry_delay(attempt)` uses exponential backoff capped at 60 seconds.
