"""Device dialogs with the original copy, controls, and platform instructions."""

from chugg.catalog import metadata
from chugg.ui_types import Dialog, Page, Platform
from chugg.views import button, e, icon


def dialog(title: str, identifier: str, content: str) -> str:
    return f'<dialog class="device-dialog" aria-labelledby="{identifier}"><div class="device-dialog-heading"><h2 id="{identifier}">{title}</h2>{button(icon("X", 20), "close", "device-dialog-close", label="Close dialog")}</div>{content}</dialog>'


def menu(standalone: bool) -> str:
    entries: list[tuple[str, str, Page | Dialog]] = [
        ("BookOpen", "Openings", "library"),
        ("ChartNoAxesColumnIncreasing", "Your progress", "progress"),
        ("ShieldCheck", "Settings and backups", "settings"),
        ("CircleHelp", "How openings are picked", "sampling"),
    ]
    if not standalone:
        entries.append(("ArrowDownToLine", "Install Chugg", "install"))
    return (
        '<nav class="menu-actions" aria-label="Main navigation">'
        + "".join(button(icon(symbol) + " " + label, action) for symbol, label, action in entries)
        + '<a href="credits.html">Credits</a></nav>'
    )


def sampling() -> str:
    return f"""<p>Chugg gives common opening families more weight, then picks a variation within the family.
        We soften the weights so less common lines still get their turn.</p>
      <p>Our catalog uses <strong>{metadata["totalGames"]:,} games</strong> from {e(metadata["source"])}. {metadata["classifiedGames"]:,} games matched a supported training line.</p>
      <p>{e(metadata["description"])}</p>
      <p>Recently shown lines are avoided when other choices are available. White or Black is chosen
        at random for each new drill. You can also choose an opening from the library.</p>
      <a class="device-dialog-help" href="credits.html">Catalog sources and credits {icon("ArrowRight", 14)}</a>
      <div class="device-dialog-section">{button("Got it " + icon("Check", 17), "close", "primary-button full-width")}</div>"""


def settings(busy: bool, message: str, error: str) -> str:
    return f"""<div class="device-dialog-icon">{icon("HardDrive", 28)}</div>
      <p>Chugg saves progress and preferences on this device. There’s no account, cloud database, or automatic sync.</p>
      <section class="device-dialog-section"><h3>Keep a copy</h3>
        <p>Export a backup before switching phones or clearing browser data. You can import it into Chugg on another device.</p>
        <div class="device-dialog-actions">{button(icon("Download", 17) + " Export backup", "export", disabled=busy)}{button(icon("Upload", 17) + " Import backup", "choose-backup", disabled=busy)}</div>
        <input hidden type="file" accept=".json,application/json" aria-label="Choose Chugg backup"/>
        <p class="device-dialog-small">Import merges results without counting the same backup twice. Existing preferences are kept. JSON files up to 2 MB.</p>
      </section><section class="device-dialog-section"><h3>Protect local progress</h3>
        <p>Ask your browser to keep Chugg’s data when device storage runs low. Backups are still useful if you clear data or lose your phone.</p>
        {button("Request persistent storage", "persist", "device-dialog-persist", disabled=busy)}</section>
      <div aria-live="polite" aria-atomic="true">{'<p class="device-dialog-small">Working…</p>' if busy else ""}{'<p class="device-dialog-notice">' + e(message) + "</p>" if message else ""}</div>
      {'<p role="alert" class="device-dialog-error">' + e(error) + "</p>" if error else ""}
      <p class="device-dialog-small"><a class="device-dialog-help" href="credits.html" target="_blank" rel="noreferrer">Credits &amp; open-source licenses</a></p>"""


def install(platform: Platform, standalone: bool) -> str:
    content = f'<div class="device-dialog-icon">{icon("Smartphone", 28)}</div><p>Add Chugg to your home screen.</p>'
    if standalone:
        content += '<p class="device-dialog-notice">You’re already using Chugg as an app.</p>'
    else:
        content += (
            '<div class="device-dialog-switch" aria-label="Phone type">'
            + "".join(
                button(
                    label,
                    "platform",
                    value=key,
                    extra=f'aria-pressed="{str(platform == key).lower()}"',
                )
                for key, label in [("iphone", "iPhone · Safari"), ("android", "Android · Chrome")]
            )
            + "</div>"
        )
        steps = (
            [
                "Open Chugg in <strong>Safari</strong>.",
                f"Tap {icon('Share', 16)} <strong>Share</strong>. Depending on your layout, open <strong>More (…)</strong> first.",
                "Scroll to <strong>Add to Home Screen</strong>. If it’s missing, find it under Edit Actions.",
                "Enable <strong>Open as Web App</strong> if shown, then tap <strong>Add</strong>.",
            ]
            if platform == "iphone"
            else [
                "Open Chugg in <strong>Chrome</strong>.",
                f"Tap {icon('EllipsisVertical', 16)} <strong>More</strong> next to the address bar.",
                "Choose <strong>Install and create shortcut</strong>, then <strong>Install</strong>. Some versions show Install app or Add to Home screen.",
                "Follow the prompts, then launch Chugg from your home screen.",
            ]
        )
        content += (
            '<ol class="device-dialog-steps">'
            + "".join(
                f"<li><span>{index}</span><div>{step}</div></li>"
                for index, step in enumerate(steps, 1)
            )
            + "</ol>"
        )
        url = (
            "https://support.apple.com/guide/iphone/open-as-web-app-iphea86e5236/ios"
            if platform == "iphone"
            else "https://support.google.com/chrome/answer/9658361?co=GENIE.Platform%3DAndroid&hl=en-GB"
        )
        content += f'<a class="device-dialog-help" href="{e(url)}" target="_blank" rel="noreferrer">{"Apple’s" if platform == "iphone" else "Google’s"} installation guide {icon("ArrowUpRight", 14)}</a>'
    return (
        content
        + '<p class="device-dialog-small">Wait for “Ready for offline practice” before disconnecting. Your progress stays in this device’s browser or installed app; export a backup to move it elsewhere.</p>'
    )
