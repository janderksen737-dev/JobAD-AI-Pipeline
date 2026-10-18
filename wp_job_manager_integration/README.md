# WP Job Manager Integration — Prototyp

Automatisiert das Veroeffentlichen einer Stellenanzeige direkt im WordPress-Backend einer
Personalvermittlung (WP Job Manager), als Alternative/Ergaenzung zu den Jobboard-Partner-APIs
(Indeed, StepStone) — die strategische Einordnung steht im (nicht in diesem Repo enthaltenen) MASTERPLAN.md.

**Warum:** ein Tech-Stack-Check der Tier-A-Zielagenturen (2026-08-04, `sales/target_agencies.md`)
zeigte, dass mehrere davon WordPress mit eigenem/Standard-Jobbörsen-Plugin nutzen, ohne erkennbare
Multiposting-Software im Hintergrund — vermutlich noch manuelles Posten. Der Umweg über Indeeds/
StepStones Partner-Programme (Wochen Wartezeit auf externe Freigabe) laesst sich fuer den Kanal
"eigene Karriereseite" umgehen: die Automatisierung nutzt ausschliesslich die eigenen Zugangsdaten
der Agentur zu ihrem eigenen System — kein Umgehen von Bot-Schutz auf einer fremden Website. Diese
Grenze bewusst einhalten: Indeed/StepStone selbst werden nie per Browser-Bot statt offizieller API
angesprochen, das waere ein Verstoss gegen deren Nutzungsbedingungen und ein Risiko fuer den
Indeed-Account des Kunden.

## Status

**Getestet und funktionsfaehig** gegen eine lokale, echte WP-Job-Manager-Installation (Docker,
nicht Teil dieses Repos, siehe unten). Noch NICHT gegen eine echte Kundeninstallation getestet — WP
Job Manager ist ein Standard-Plugin, aber jede Agentur-Website hat eigene Login-URLs, ggf. 2FA, ggf.
ein anderes/individuelles Plugin (z.B. aero-hp.com und expertum.de haben eigene, firmenspezifische
Plugins statt WP Job Manager — fuer die muesste das Skript pro Firma angepasst werden, siehe
Tradeoff in MASTERPLAN.md).

## Wie getestet wurde

Docker-Compose-Stack mit `wordpress:latest` + `mysql:8.0`, WP Job Manager + Classic Editor per
WP-CLI installiert (kein bestehendes Repo-Setup — rein lokal, temporaer, nicht Teil des Git-Repos).
`demo_post_job.py` loggt sich ein, fuellt Titel/Beschreibung/Standort/Firma/Beschaeftigungsart/
Bewerbungs-E-Mail und veroeffentlicht — Ergebnis live per curl gegen die oeffentliche Anzeige-URL
verifiziert (Standort, Aufgaben-Stichwort, Beschaeftigungsart, Firmenbeschreibung alle korrekt
uebernommen).

## Bekannte Playwright/Chromium-Eigenheit (gefunden + geloest)

Auf der WP-Login-Seite fuehrt `page.fill()`/Tastatur-Simulation auf das Passwortfeld zu einem
reproduzierbaren Bug: der eingegebene Wert landet im benachbarten Benutzername-Feld statt im
Passwortfeld selbst. Direktes Setzen des Werts per JavaScript + Event-Dispatch (`_set_value()` in
`wp_job_manager_client.py`) umgeht das zuverlaessig.

Zweite Eigenheit: die Beschaeftigungsart-Checkbox muss frueh im Ablauf gesetzt werden (direkt nach
dem Laden der Seite, mit kurzer Wartezeit) statt kurz vor dem Veroeffentlichen — sonst kollidiert
eine dadurch ausgeloeste JS-Reaktion von WP Job Manager mit dem Publish-Klick, und WordPress springt
zurueck auf ein leeres Formular statt zu veroeffentlichen.

## Nicht enthalten / bewusst offen

- Kein Login-Session-Handling ueber mehrere Anzeigen hinweg (fuer Produktionsreife: Session/Cookies
  wiederverwenden statt jedes Mal neu einzuloggen)
- Kein Umgang mit 2FA — falls eine echte Kundenseite 2FA erfordert, muesste das gesondert geloest
  werden (z.B. App-Passwoerter statt normalem Login, WordPress unterstuetzt das nativ)
- Kein Erkennen von Custom-Plugins wie bei aero-hp/expertum — nur WP Job Manager als Standardfall
- Freigabe-Schritt (siehe MASTERPLAN.md, Freigabe-Designprinzip): `publish=False` legt einen Entwurf
  an statt live zu schalten — Verdrahtung mit dem Freigabe-Schritt der Webapp noch nicht gebaut
