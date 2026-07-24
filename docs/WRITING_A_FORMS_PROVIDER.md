# Writing a Forms Provider

This is the developer guide for handling form submissions with your
own destination — a webhook, a queue, a CRM, anything. A provider is
one factory implementing one contract; the endpoint, the editor and
the publish flow never change.

For the operator's view (configuration, behaviour, failure semantics),
see the Forms section of [ADMIN_GUIDE.md](ADMIN_GUIDE.md).

## The lifecycle

The endpoint owns everything before acceptance: the protocol, the
layered spam protection, server-side validation and the visitor's
answer. A provider owns everything after it:

```text
validate → accept → provider.handle(submission, form)
```

New spam layers, new field types and response changes never touch
providers — they only ever receive accepted submissions.

## The contract

```python
from cms_core.forms import FORMS_CONTRACT_VERSION, FormContext, FormSubmission


class QueueProvider:
    contract_version = FORMS_CONTRACT_VERSION

    def handle(
        self, submission: FormSubmission, form: FormContext
    ) -> None: ...  # deliver, store, forward — raise on failure
```

- `submission` carries the operational fields (id, received moment,
  page, section, language) and the visitor's `values` — plain text,
  treat them as opaque.
- `form` carries what the form declared: `heading`, the configured
  `notify` address and whether the operator asked to `store`.
- `contract_version` is validated at selection time; a mismatch
  refuses loudly before anything runs.

## Registration

```python
from cms_core.extensions import Extension


def factory() -> QueueProvider:
    return QueueProvider()


extension = Extension(name="queue-forms", forms_providers={"queue": factory})
```

The project activates the extension and selects the provider:

```toml
extensions = ["sardine_forms_queue:extension"]

[forms]
endpoint = "https://panel.example.com/forms/submit"
provider = "queue"
```

## Rules a provider must keep

- It only ever sees accepted submissions and must treat the values as
  plain text.
- It must not answer the visitor — its outcome never changes the HTTP
  response; the endpoint contains and audits a raised failure.
- Failures must raise rather than being swallowed silently — the audit
  trail is how operators learn something went wrong.
- Credentials come from the environment, never from configuration, and
  never enter logs or the audit trail.

The repository ships a conformance suite
(`tests/test_forms_provider_contract.py`) that runs these rules
against every provider, including an extension-registered one — run it
against yours while developing.

Ecosystem naming for published providers: `sardine-forms-<name>`
(see [ECOSYSTEM.md](ECOSYSTEM.md)).
