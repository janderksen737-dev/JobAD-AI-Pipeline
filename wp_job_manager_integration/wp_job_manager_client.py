"""
Prototyp: veroeffentlicht eine Stellenanzeige direkt im WordPress-Backend einer
Personalvermittlung (WP Job Manager) - als Alternative/Ergaenzung zu den
Jobboard-Partner-APIs (Indeed, StepStone), fuer die eine externe Freigabe noetig ist.

Kein Partner-Programm noetig: die Automatisierung nutzt ausschliesslich die eigenen
Zugangsdaten der Agentur zu ihrem eigenen Backend - kein Umgehen von Bot-Schutz auf
fremden Websites (Indeed/StepStone selbst werden weiterhin nur ueber ihre offiziellen
Schnittstellen angesprochen, nie per Browser-Bot).

Getestet gegen eine lokale WP-Job-Manager-Testinstallation (Docker), nicht gegen einen
echten Kunden - analog zum StepStone-Prototyp: zeigt, dass es technisch funktioniert,
bevor ein echter Kunde seine Zugangsdaten teilt.
"""
import html

from playwright.sync_api import sync_playwright

_SET_VALUE_JS = """(el, val) => {
    el.value = val;
    el.dispatchEvent(new Event('input', {bubbles: true}));
    el.dispatchEvent(new Event('change', {bubbles: true}));
}"""


def _set_value(page, selector: str, value: str) -> None:
    """Setzt den Feldwert direkt per JS statt ueber Playwrights fill()/Tastatur-Simulation.

    Auf der WP-Login-Seite fuehrt fill() auf #user_pass zu einem reproduzierbaren
    Chromium-Bug: der eingegebene Wert landet im benachbarten #user_login-Feld statt im
    Passwortfeld selbst (vermutlich Interferenz zwischen Chromiums Autofill-Heuristik und
    dem von WordPress geladenen zxcvbn-Skript). Direktes Setzen per JS + Event-Dispatch
    umgeht das zuverlaessig und ist fuer Formularfelder generell genauso wirksam."""
    page.eval_on_selector(selector, _SET_VALUE_JS, value)

# Anzeige-Namen der WP-Job-Manager-Taxonomie "job_listing_type" -> DOM-IDs. Diese IDs
# sind KEINE stabilen Konstanten ueber verschiedene WordPress-Installationen hinweg
# (Taxonomie-Term-IDs werden pro Installation vergeben) - vor echtem Kundeneinsatz pro
# Installation neu auslesen (siehe _discover_employment_type_ids()).
_KNOWN_EMPLOYMENT_TYPE_LABELS = {
    "Vollzeit": "Full Time",
    "Teilzeit": "Part Time",
    "Praktikum": "Internship",
    "Freelance": "Freelance",
    "Befristet": "Temporary",
}


class WPJobManagerError(Exception):
    """Wird geworfen, wenn Login oder Veroeffentlichung fehlschlaegt."""


def _discover_employment_type_ids(page) -> dict[str, str]:
    """Liest die tatsaechlichen Radio-IDs der Job-Type-Taxonomie live aus der Seite,
    statt sie hart zu kodieren - Taxonomie-Term-IDs unterscheiden sich pro Installation."""
    rows = page.eval_on_selector_all(
        'input[name="tax_input[job_listing_type]"]',
        "els => els.map(el => ({id: el.id, label: el.closest('label')?.textContent.trim()}))",
    )
    return {row["label"]: row["id"] for row in rows if row["label"]}


def _build_description_html(tasks: list[str], profile: list[str]) -> str:
    """html.escape() auf jeden Textbaustein: ohne das koennte ein "<" im Kundentext das
    Layout der Karriereseite des Kunden zerstoeren oder als Markup dort landen."""
    tasks_html = "".join(f"<li>{html.escape(t)}</li>" for t in tasks)
    profile_html = "".join(f"<li>{html.escape(p)}</li>" for p in profile)
    return (
        f"<h3>Ihre Aufgaben</h3><ul>{tasks_html}</ul>"
        f"<h3>Ihr Profil</h3><ul>{profile_html}</ul>"
    )


def post_job_to_wordpress(
    wp_base_url: str,
    username: str,
    password: str,
    job_title: str,
    location: str,
    tasks: list[str],
    profile: list[str],
    company_name: str,
    employment_type: str = "",
    company_website: str = "",
    application_email: str = "",
    publish: bool = True,
    headless: bool = True,
) -> str:
    """Loggt sich ins WordPress-Backend ein, legt einen neuen Job-Listing-Eintrag ueber
    WP Job Manager an und veroeffentlicht ihn. Nutzt dieselben strukturierten Felder wie
    build_indeed_payload()/build_stepstone_payload() - nur ein zusaetzlicher Zielkanal,
    keine neue KI-Logik. Gibt die URL des veroeffentlichten Eintrags zurueck.

    publish=False legt die Anzeige nur als Entwurf an (fuer die Freigabe-Pruefung durch
    die Agentur, bevor sie live geht - siehe MASTERPLAN.md, Freigabe-Designprinzip)."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()

        page.goto(f"{wp_base_url}/wp-login.php")
        _set_value(page, "#user_login", username)
        _set_value(page, "#user_pass", password)
        page.click("#wp-submit")
        try:
            page.wait_for_selector("#wpadminbar", timeout=8000)
        except Exception as exc:
            browser.close()
            raise WPJobManagerError(f"Login fehlgeschlagen fuer {wp_base_url}") from exc

        page.goto(f"{wp_base_url}/wp-admin/post-new.php?post_type=job_listing")

        # Radio zuerst setzen, mit kurzer Wartezeit: WP Job Manager haengt daran eine
        # JS-Reaktion (Conditional Fields), die - spaeter im Ablauf ausgefuehrt - mit dem
        # Publish-Klick kollidiert (WordPress bounct dann zurueck auf ein leeres
        # post-new.php statt zu veroeffentlichen). Frueh setzen + kurz warten vermeidet das.
        if employment_type:
            type_ids = _discover_employment_type_ids(page)
            label = _KNOWN_EMPLOYMENT_TYPE_LABELS.get(employment_type, employment_type)
            if radio_id := type_ids.get(label):
                page.check(f"#{radio_id}")
                page.wait_for_timeout(1500)

        page.fill("#title", job_title)

        page.click("#content-html")  # Text-/Code-Ansicht statt TinyMCE-Iframe
        page.fill("#content", _build_description_html(tasks, profile))

        page.fill("#_job_location", location)
        page.fill("#_company_name", company_name)
        if company_website:
            page.fill("#_company_website", company_website)
        if application_email:
            page.fill("#_application", application_email)

        page.click("#publish" if publish else "#save-post")
        page.wait_for_load_state("networkidle", timeout=15000)
        if "post.php?post=" not in page.url:
            browser.close()
            raise WPJobManagerError("Veroeffentlichen fehlgeschlagen - keine Weiterleitung zur Edit-Seite")

        permalink = page.eval_on_selector(
            'a[href*="job_listing="], #edit-slug-box a', "el => el?.href"
        )
        edit_url = page.url

        browser.close()
        return permalink or edit_url
