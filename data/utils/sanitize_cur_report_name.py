import re


def sanitize_report_name(name: str) -> str:
    """
    Sanitize report name to meet AWS CUR regex:
    [0-9A-Za-z!\-_.*'()]+
    """
    # Replace spaces with '-'
    name = name.replace(" ", "-")
    # Strip out any disallowed characters
    return re.sub(r"[^0-9A-Za-z!\-_.()*']", "", name)


print(sanitize_report_name("new report {} name"))
