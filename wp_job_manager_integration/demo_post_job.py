"""
Manueller Testlauf gegen eine echte (lokale) WP-Job-Manager-Installation - kein Teil der
regulaeren pytest-Suite, weil eine laufende WordPress-Instanz Voraussetzung ist (siehe
README in diesem Ordner). Nutzt dieselben Beispieldaten wie die uebrige Pipeline-Tests
(Bremen-Konstrukteur-Beispiel), um Ergebnisse vergleichbar zu machen.

Aufruf:
    .venv/bin/python demo_post_job.py
"""
from wp_job_manager_client import post_job_to_wordpress

if __name__ == "__main__":
    url = post_job_to_wordpress(
        wp_base_url="http://localhost:8930",
        username="recruitflow_test",
        password="RecruitFlowTest2026!",
        job_title="Konstrukteur (m/w/d)",
        location="Bremen",
        tasks=[
            "Konstruktion von Strukturbauteilen in CATIA V5",
            "Erstellung von Fertigungszeichnungen",
            "Abstimmung mit dem Qualitätsmanagement",
        ],
        profile=[
            "Abgeschlossenes Studium Maschinenbau oder vergleichbar",
            "Mindestens 3 Jahre Erfahrung in der Strukturkonstruktion",
            "Sehr gute CATIA V5 Kenntnisse",
        ],
        company_name="Unternehmen der Luft- und Raumfahrtbranche (Luftfahrt-Zulieferer)",
        employment_type="Vollzeit",
        application_email="bewerbung@talentbridge-beispiel.de",
        headless=True,
    )
    print(f"Veroeffentlicht: {url}")
