"""Human-readable views of workflow records; the envelope retains exact data."""
import html
import shlex


# Integrity bookkeeping belongs in the machine envelope, not the issue timeline.
INTERNAL = {"version", "revision", "contract_revision", "checkpoint"}
LABELS = {
    "argv": "Command (shell-quoted)",
    "check_manifest": "Verification checks",
    "acceptance_matrix": "Acceptance criteria",
    "coverage": "Requirement coverage",
    "facts": "Evidence",
    "source_context": "Source context",
    "review_reason": "Manual review required",
}


def label(key):
    return LABELS.get(key, key if key.isupper() else key.replace("_", " ").capitalize())


def scalar(value):
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if value is None:
        return "None"
    # Do not allow task text to introduce HTML envelope markers or hide content.
    return html.escape(str(value), quote=False)


def code(value):
    # A fence longer than any backtick run keeps arbitrary argv values literal.
    fence = "`"
    while fence in value:
        fence += "`"
    return fence + " " + value + " " + fence


def lines(value, depth=0):
    indent = "    " * depth
    if isinstance(value, dict):
        result = []
        for key, item in value.items():
            heading = indent + "- **" + scalar(label(key)) + ":**"
            if key == "argv" and isinstance(item, list) and all(isinstance(x, str) for x in item):
                result.append(heading + " " + code(shlex.join(item)))
            elif isinstance(item, (dict, list)) and item:
                result.append(heading)
                result.extend(lines(item, depth + 1))
            else:
                result.append(heading + " " + ("None" if isinstance(item, (dict, list)) else scalar(item)).replace("\n", "\n" + indent + "  "))
        return result
    if isinstance(value, list):
        result = []
        for index, item in enumerate(value, 1):
            if isinstance(item, (dict, list)):
                nested = lines(item, depth + 1)
                first = nested[0].lstrip().removeprefix("- ") if nested else "None"
                result.append(indent + str(index) + ". " + first)
                result.extend(nested[1:])
            else:
                result.append(indent + "- " + scalar(item).replace("\n", "\n" + indent + "  "))
        return result
    return [scalar(value)]


def record_markdown(kind, record):
    sections = ["## " + kind.title()]
    for key, value in record.items():
        if key in INTERNAL:
            continue
        sections.append("### " + label(key))
        if key == "steps" and isinstance(value, list):
            sections.append("\n".join(str(i) + ". " + scalar(step).replace("\n", "\n   ")
                                      for i, step in enumerate(value, 1)) or "None")
        else:
            sections.append("\n".join(lines(value)) if value else (scalar(value) if value in (False, 0) else "None"))
    return "\n\n".join(sections)
