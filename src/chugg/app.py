"""Browser application controller; domain rules remain independently testable."""

import asyncio
import json
from collections.abc import Coroutine
from datetime import UTC, datetime
from math import isfinite
from typing import TypedDict, assert_never, cast

from chugg import dialogs, views
from chugg.browser import Host, ProxyFactory
from chugg.catalog import openings
from chugg.models import LineProgress
from chugg.progress import count_sample, now_ms
from chugg.sampling import (
    EXPLORATION_MAX,
    EXPLORATION_MIN,
    available_lines,
    sample_opening,
    sample_side,
)
from chugg.storage import Repository
from chugg.trainer import Drill
from chugg.ui_types import Action, Dialog, Page, Platform, SettingsAction, is_action


class Environment(TypedDict):
    standalone: bool
    android: bool
    online: bool


class OfflineState(TypedDict):
    ready: bool
    refresh: bool
    error: bool


class App:
    def __init__(self, host: Host, proxy: ProxyFactory) -> None:
        self.host = host
        self.repository = Repository(host, proxy)
        self.environment = cast(Environment, json.loads(host.environment()))
        self.offline: OfflineState = {"ready": False, "refresh": False, "error": False}
        self.page: Page = "practice"
        self.progress: list[LineProgress] = []
        self.sampled: dict[str, int] = {}
        self.recent_ids: list[str] = []
        self.exploration = EXPLORATION_MIN
        self.drill: Drill | None = None
        self.ready = False
        self.dialog: Dialog | None = None
        self.query = ""
        self.family = ""
        self.error = ""
        self.busy = False
        self.settings_message = ""
        self.settings_error = ""
        self.platform: Platform = "android" if self.environment["android"] else "iphone"
        self.tasks: set[asyncio.Task[None]] = set()
        self.timer: asyncio.Task[None] | None = None
        # Keep the callback alive for the lifetime of the application.
        self.callback = proxy(self.dispatch_browser)
        host.bind(self.callback)

    def spawn(self, coroutine: Coroutine[object, object, None]) -> asyncio.Task[None]:
        task = asyncio.create_task(coroutine)
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)
        return task

    async def initialize(self) -> None:
        self.render()
        try:
            snapshot = await self.repository.snapshot()
            self.progress, self.sampled = snapshot["progress"], snapshot["sampled"]
        except Exception:
            self.error = (
                "Device storage is unavailable. You can practice, but progress may not be saved."
            )
        self.ready = True
        self.render()

    def render(self, focus: str = "") -> None:
        body = "" if self.drill or self.page == "practice" else views.header()
        if self.error:
            body += f'<div class="error-banner" role="alert"><span>{views.e(self.error)}</span>{views.button(views.icon("X", 16), "dismiss", "icon-button", label="Dismiss notification")}</div>'
        if self.drill:
            body += views.trainer(self.drill)
        else:
            match self.page:
                case "library":
                    body += views.library(self.query, self.family, self.progress)
                case "progress":
                    body += views.progress_page(self.progress, self.host.date)
                case "practice":
                    body += views.home(
                        self.ready, self.exploration, len(available_lines(openings, self.sampled))
                    )
                case _:
                    assert_never(self.page)
        body += '<div class="update-notice">' + self.offline_view() + "</div>"
        if self.dialog:
            match self.dialog:
                case "menu":
                    title, identifier, content = (
                        "Chugg",
                        "menu-title",
                        dialogs.menu(self.environment["standalone"]),
                    )
                case "settings":
                    title, identifier, content = (
                        "Settings and backups",
                        "data-title",
                        dialogs.settings(self.busy, self.settings_message, self.settings_error),
                    )
                case "sampling":
                    title, identifier, content = (
                        "How Chugg picks your opening",
                        "sampling-title",
                        dialogs.sampling(),
                    )
                case "install":
                    title, identifier, content = (
                        "Install Chugg",
                        "install-title",
                        dialogs.install(self.platform, self.environment["standalone"]),
                    )
                case "moves":
                    title, identifier, content = (
                        "Moves",
                        "moves-title",
                        views.moves_dialog(self.drill) if self.drill else "",
                    )
                case _:
                    assert_never(self.dialog)
            body += dialogs.dialog(title, identifier, content)
        self.host.render(
            f'<div class="app-shell" data-training="{str(self.drill is not None).lower()}">{body}</div>',
            focus,
        )

    def offline_view(self) -> str:
        if not self.offline["refresh"] and not self.offline["error"]:
            return ""
        message = (
            "Offline setup unavailable — try reloading online"
            if self.offline["error"]
            else "You’re offline"
            if not self.environment["online"]
            else "Ready for offline practice"
            if self.offline["ready"]
            else "Preparing offline practice…"
        )
        update = ""
        if self.offline["refresh"]:
            update = (
                "<span>Update ready after your drill</span>"
                if self.drill
                else views.button("Update Chugg", "update", "text-button")
            )
        return f'<div class="offline-status" role="status" style="font-size:12px;display:flex;gap:10px;align-items:center;flex-wrap:wrap"><span>{message}</span>{update}</div>'

    def cancel_timer(self) -> None:
        if self.timer:
            self.timer.cancel()
            self.timer = None

    def schedule(self) -> None:
        self.cancel_timer()
        drill = self.drill
        if not drill:
            return
        if drill.done:
            if not drill.reported:
                drill.reported = True
                self.spawn(self.save(drill))
        elif drill.introducing or not drill.own_turn:
            self.timer = self.spawn(self.advance(drill, 1.0 if drill.introducing else 0.65))

    async def advance(self, drill: Drill, delay: float) -> None:
        await asyncio.sleep(delay)
        self.timer = None
        if self.drill is not drill:
            return
        focus = ".training-title" if drill.introducing else ""
        if drill.introducing:
            drill.introducing = False
        else:
            drill.reply()
        self.render(focus)
        self.schedule()

    async def save(self, drill: Drill) -> None:
        try:
            self.progress = (
                await self.repository.record(
                    {
                        "lineId": drill.line["id"],
                        "side": drill.side,
                        "hints": drill.hints,
                        "mistakes": drill.mistakes,
                        "completedAt": now_ms(),
                    }
                )
            )["progress"]
        except Exception:
            self.error = "Your line is complete, but we couldn’t save this result. Export a backup from Settings if device storage is full."
        self.render()

    async def save_sample(self, line_id: str) -> None:
        try:
            self.sampled = (await self.repository.record_sample(line_id))["sampled"]
        except Exception:
            # The drill continues; this draw is only missing from a future session's tally.
            self.error = "We couldn’t save this draw, so it may come up again after a reload."
            self.render()

    async def reset_history(self) -> None:
        try:
            self.sampled = (await self.repository.reset_samples())["sampled"]
        except Exception:
            self.error = "We couldn’t clear your sampling history on this device."
        self.render()

    def dispatch_browser(self, action: str, value: str) -> None:
        # JavaScript supplies untyped strings; ignore unknown actions as before.
        if is_action(action):
            self.dispatch(action, value)

    def dispatch(self, action: Action, value: str) -> None:
        # Event handlers stay synchronous; only explicit storage operations launch tasks.
        focus = ""
        match action:
            case "practice" | "library" | "progress":
                self.cancel_timer()
                self.drill, self.dialog, self.page = None, None, action
                self.host.scroll()
            case "start":
                line = (
                    next((row for row in openings if row["id"] == value), None)
                    if value
                    else sample_opening(
                        openings,
                        recent_ids=self.recent_ids,
                        sampled=self.sampled,
                        exploration=self.exploration,
                    )
                )
                if not line:
                    if value:
                        return
                    # Every line has been drawn its limit: send them home to reset.
                    self.cancel_timer()
                    self.drill = None
                else:
                    self.drill = Drill(line, sample_side())
                    self.recent_ids = [line["id"], *self.recent_ids][:5]
                    if not value:
                        # Only sampled draws count. Choosing a line from the library is
                        # the user's own pick, not one of ours to retire.
                        self.sampled = count_sample(line["id"], self.sampled)
                        self.spawn(self.save_sample(line["id"]))
                    self.schedule()
                self.dialog, self.page = None, "practice"
                self.host.scroll()
            case "exploration":
                try:
                    alpha = float(value)
                except ValueError:
                    return
                if not isfinite(alpha):
                    return
                self.exploration = min(EXPLORATION_MAX, max(EXPLORATION_MIN, alpha))
            case "reset-history":
                self.sampled = {}
                self.recent_ids = []
                self.spawn(self.reset_history())
            case "replay":
                if self.drill:
                    self.drill = Drill(self.drill.line, self.drill.side, introducing=False)
                    self.schedule()
            case "square" | "move" | "hint" | "promote" | "cancel-promotion":
                if not self.drill:
                    return
                previous_ply = self.drill.ply
                match action:
                    case "square":
                        self.drill.select(value)
                    case "move":
                        self.drill.move(value[:2], value[2:4])
                    case "hint":
                        self.drill.show_hint()
                    case "cancel-promotion":
                        self.drill.promotion = None
                    case "promote":
                        if self.drill.promotion:
                            self.drill.attempt(*self.drill.promotion, value)
                    case _:
                        assert_never(action)
                if self.drill.ply != previous_ply:
                    self.schedule()
            case "menu" | "settings" | "sampling" | "install" | "moves":
                self.dialog = action
                if action == "settings":
                    self.settings_message = self.settings_error = ""
                if action == "install":
                    self.platform = "android" if self.environment["android"] else "iphone"
            case "close":
                previous = self.dialog
                self.dialog = None
                focus = '[data-action="moves"]' if previous == "moves" else '[data-action="menu"]'
            case "search":
                self.query = value
            case "family":
                self.family = value
            case "clear-filters":
                self.query = self.family = ""
            case "platform":
                if value not in ("iphone", "android"):
                    return
                self.platform = value
            case "dismiss":
                self.error = ""
            case "offline":
                self.offline = cast(OfflineState, json.loads(value))
            case "online":
                self.environment["online"] = value == "true"
            case "export" | "import" | "persist":
                if not self.busy:
                    self.spawn(self.settings_action(action, value))
            case "file-error":
                self.settings_error = value
            case "update":
                if not self.drill:
                    self.spawn(self.update())
            case _:
                assert_never(action)
        self.render(focus)

    async def settings_action(self, action: SettingsAction, value: str) -> None:
        self.busy = True
        self.settings_message = self.settings_error = ""
        self.render()
        try:
            if action == "export":
                self.host.download(
                    await self.repository.export(),
                    f"chugg-backup-{datetime.now(UTC).date().isoformat()}.json",
                )
                self.settings_message = (
                    "Backup prepared. Keep the downloaded JSON file somewhere safe."
                )
            elif action == "import":
                await self.repository.import_text(value)
                self.settings_message = (
                    "Backup imported. Your newest results and highest completion counts were kept."
                )
                try:
                    self.progress = (await self.repository.snapshot())["progress"]
                except Exception:
                    self.error = "We couldn’t load your imported progress. Please try again."
            elif action == "persist":
                granted = await self.host.persist()
                self.settings_message = (
                    "Persistent storage is enabled for Chugg. Keep exporting backups for extra peace of mind."
                    if granted
                    else "This browser hasn’t granted persistent storage. Export a backup to protect your local progress."
                )
            else:
                assert_never(action)
        except Exception as error:
            self.settings_error = str(error) or "Device storage is unavailable. Please try again."
        finally:
            self.busy = False
            self.render()

    async def update(self) -> None:
        try:
            await self.host.update()
        except Exception:
            self.offline["error"] = True
            self.render()
