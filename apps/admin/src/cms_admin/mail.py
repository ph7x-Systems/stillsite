"""Outbound email (ADR-0032): a pluggable transport, optional by default.

``SARDINE_MAIL_TRANSPORT`` names the transport. The bundled baseline is
``smtp`` (standard library; ``SARDINE_SMTP_URL`` =
``smtp://user:pass@host:587`` for STARTTLS or ``smtps://…:465``, plus
``SARDINE_MAIL_FROM``); any other name resolves to a mail transport an
activated extension registers (``Extension.mail_transports``) — that is
where passwordless provider APIs live. Unconfigured means email is off
and every email-dependent feature degrades gracefully. Messages are
plain text, localized by the caller; no HTML, no tracking.
"""

import smtplib
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from email.message import EmailMessage
from urllib.parse import unquote, urlsplit

SMTP_TIMEOUT_SECONDS = 10.0


@dataclass(frozen=True, slots=True)
class Mailer:
    host: str
    port: int
    username: str | None
    password: str | None
    implicit_tls: bool
    sender: str

    @classmethod
    def from_settings(cls, smtp_url: str | None, mail_from: str | None) -> "Mailer | None":
        """None when email is off; raises ValueError on a broken URL —
        a half-configured transport must fail at startup, not at send."""
        if not smtp_url or not mail_from:
            return None
        parts = urlsplit(smtp_url)
        if parts.scheme not in {"smtp", "smtps"} or not parts.hostname:
            raise ValueError("SARDINE_SMTP_URL must be smtp://host[:port] or smtps://host[:port]")
        default_port = 465 if parts.scheme == "smtps" else 587
        return cls(
            host=parts.hostname,
            port=parts.port or default_port,
            username=unquote(parts.username) if parts.username else None,
            password=unquote(parts.password) if parts.password else None,
            implicit_tls=parts.scheme == "smtps",
            sender=mail_from,
        )

    def send(self, to: str, subject: str, body: str) -> None:
        """Deliver one plain-text message; exceptions are the caller's to
        contain (never let delivery block an editorial action)."""
        message = EmailMessage()
        message["From"] = self.sender
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)
        if self.implicit_tls:
            with smtplib.SMTP_SSL(self.host, self.port, timeout=SMTP_TIMEOUT_SECONDS) as server:
                self._deliver(server, message)
        else:
            with smtplib.SMTP(self.host, self.port, timeout=SMTP_TIMEOUT_SECONDS) as server:
                server.starttls()
                self._deliver(server, message)

    def _deliver(self, server: smtplib.SMTP, message: EmailMessage) -> None:
        if self.username and self.password:
            server.login(self.username, self.password)
        server.send_message(message)


@dataclass(frozen=True, slots=True)
class ExtensionMailer:
    """Adapts an extension's ``MailSender`` callable to the panel's
    ``send`` surface (ADR-0032)."""

    deliver: "Callable[[str, str, str], None]"

    def send(self, to: str, subject: str, body: str) -> None:
        self.deliver(to, subject, body)


def resolve_mailer(
    transport: str,
    smtp_url: str | None,
    mail_from: str | None,
    extension_transports: "Mapping[str, Callable[[], Callable[[str, str, str], None]]]",
) -> "Mailer | ExtensionMailer | None":
    """The one place transport names resolve. ``smtp`` unconfigured means
    email off; an unknown non-smtp name is a startup error — a configured
    transport must never vanish silently."""
    if transport == "smtp":
        return Mailer.from_settings(smtp_url, mail_from)
    factory = extension_transports.get(transport)
    if factory is None:
        raise ValueError(f"mail transport {transport!r} is not offered by any activated extension")
    return ExtensionMailer(factory())
