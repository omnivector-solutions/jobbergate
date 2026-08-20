"""
Prompt backend that relays application questions to a Jobbergate Form Runner bridge.

This is the cluster-side half of the web question flow: the ``create-web-runner`` command runs
inside a Slurm job and resolves the application prompts through the Form Runner service instead
of an interactive terminal. Questions are served one at a time; each answer is validated here
with the very same ``inquirer`` validators the terminal flow uses (so ``Integer`` ranges and
``File``/``Directory`` existence checks run on the *cluster* filesystem), and rejected answers
are re-asked with the validation message relayed back to the web form.
"""

from typing import Any, Dict, List

import httpx
import inquirer.errors

from jobbergate_cli.exceptions import Abort

# Map inquirer question kinds to the wire types understood by the web form
_KIND_MAP = {
    "text": "Text",
    "list": "List",
    "checkbox": "Checkbox",
    "confirm": "Confirm",
    "path": "File",
}


def _jsonable(value: Any) -> Any:
    """Coerce a resolved inquirer value into something JSON-serializable."""
    if isinstance(value, (str, int, float, bool, type(None))):
        return value
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return str(value)


class BridgePrompter:
    """
    A :data:`~jobbergate_cli.subapps.applications.tools.PromptBackend` that serves prompts
    through the Form Runner internal bridge, one question at a time.
    """

    def __init__(self, *, bridge_url: str, session_id: str, session_secret: str):
        self._client = httpx.Client(
            base_url=f"{bridge_url.rstrip('/')}/form-runner/internal/sessions/{session_id}",
            headers={"X-Session-Secret": session_secret},
            timeout=httpx.Timeout(60.0, read=60.0),
        )

    # -- bridge plumbing ---------------------------------------------------------------

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        response = self._client.request(method, path, **kwargs)
        Abort.require_condition(
            response.status_code < 400,
            f"The form-runner bridge rejected a {method} {path} request with {response.status_code}",
            raise_kwargs={"subject": "Form runner bridge error", "support": True},
        )
        return response

    def fetch_context(self) -> Dict[str, Any]:
        """Fetch the session context (application selection, token, options) from the bridge."""
        return self._request("GET", "/context").json()

    def report_done(self, result: Dict[str, Any]) -> None:
        """Report a successful outcome for the session."""
        self._request("POST", "/finish", json={"status": "completed", "result": result})

    def report_failed(self, message: str) -> None:
        """Report a failed outcome for the session."""
        # A best-effort call: failures here must not mask the original error
        try:
            self._client.post("/finish", json={"status": "failed", "message": message})
        except httpx.HTTPError:
            pass

    # -- prompt backend ----------------------------------------------------------------

    def __call__(self, prompts: List[Any]) -> Dict[str, Any]:
        answers: Dict[str, Any] = {}
        for question in prompts:
            # inquirer questions resolve message/default/ignore against the accumulated
            # answers dict, which is how BooleanList conditionals and Const auto-answers
            # behave exactly as they do on the terminal.
            question.answers = answers
            if question.ignore:
                already_answered = question.name in answers
                answers[question.name] = question.default
                # A skipped BooleanList child resolves to the sibling's already-given
                # answer: only report genuinely auto-answered values (e.g. Const)
                if not already_answered:
                    self._request(
                        "POST",
                        "/questions",
                        json={"question": self._serialize(question), "auto": True, "value": _jsonable(question.default)},
                    )
                continue
            answers[question.name] = self._ask(question)
        return answers

    def _serialize(self, question: Any) -> Dict[str, Any]:
        message = question.message or question.name
        # Checkbox messages carry a terminal keybinding hint that is meaningless on the web
        message = message.split(" [SPACE: Select", 1)[0]
        payload: Dict[str, Any] = {
            "type": _KIND_MAP.get(getattr(question, "kind", "text"), "Text"),
            "variablename": question.name,
            "message": message,
            "default": _jsonable(question.default),
        }
        if payload["type"] in ("List", "Checkbox"):
            payload["choices"] = [_jsonable(choice) for choice in question.choices]
        return payload

    def _ask(self, question: Any) -> Any:
        self._request("POST", "/questions", json={"question": self._serialize(question), "auto": False})
        while True:
            response = self._request("GET", "/answer", params={"wait": 30})
            if response.status_code == 204:
                continue  # long-poll timed out with no answer yet; keep waiting
            value = response.json()["value"]
            try:
                question.validate(value)
            except inquirer.errors.ValidationError as err:
                reason = getattr(err, "reason", None) or f"{value!r} is not a valid value"
                self._request("POST", "/verdict", json={"accepted": False, "message": str(reason)})
                continue
            self._request("POST", "/verdict", json={"accepted": True, "value": _jsonable(value)})
            return value
