import json
from fastapi.templating import Jinja2Templates

_MONTHS = {
    "jan": "January", "feb": "February", "mar": "March",
    "apr": "April",   "may": "May",      "jun": "June",
    "jul": "July",    "aug": "August",   "sep": "September",
    "oct": "October", "nov": "November", "dec": "December",
}

_templates: Jinja2Templates | None = None


def get_templates() -> Jinja2Templates:
    global _templates
    if _templates is None:
        _templates = Jinja2Templates(directory="templates")
        env = _templates.env

        def from_json(s):
            try:
                return json.loads(s) if s else []
            except Exception:
                return []

        def join_json(s):
            return ", ".join(from_json(s))

        def months_json(s):
            return ", ".join(_MONTHS.get(m.lower(), m.capitalize()) for m in from_json(s))

        env.filters["from_json"]   = from_json
        env.filters["join_json"]   = join_json
        env.filters["months_json"] = months_json

    return _templates
