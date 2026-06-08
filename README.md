# DBA Prisekspert (Scraper GUI)

Dette projekt er et smart lille værktøj til at skrabe (hente) annoncer fra DBA (Den Blå Avis) og samle dem i en pæn, læsbar Markdown-tabel. Programmet er udstyret med en grafisk brugerflade (GUI), så det er let at bruge uden at kende til kodning.

Det blev oprindeligt bygget til at finde de bedste priser på "Fender Stratocaster"-guitarer, men kan bruges til enhver søgning på DBA!

## ✨ Funktioner

- **Grafisk Brugerflade:** Indtast din søgning direkte i et simpelt vindue.
- **Søg på Fritekst eller URL:** Søg på f.eks. `fender stratocaster` eller indsæt et direkte link til en specifik DBA-kategori.
- **Dyb Kategorifiltrering:** Inden resultaterne gemmes, viser programmet dig en pop-up med alle de underkategorier, der blev fundet. Du kan fjerne fluebenet fra dem, du ikke er interesseret i (f.eks. for at sortere reservedele eller forstærkere fra).
- **Hurtig & Asynkron:** Henter data via flere tråde samtidigt (op til 10 sider ad gangen).
- **Markdown Output:** Gemmer resultaterne i en flot, letlæselig tabel med billed-links, direkte links til annoncerne, alder, stand, pris og by.

## 🚀 Installation & Brug (Nemmeste metode)

Du behøver ikke have Python installeret for at køre programmet.

1. Gå til **[Releases](https://github.com/bosund/DBA-Prisekspert/releases/latest)**.
2. Download den seneste fil: `dba_gui.exe`.
3. Dobbeltklik på filen for at starte programmet.
4. Udfyld dine søgekriterier og tryk på **Start Scraping**.

## 💻 Kørsel fra Kildekode (For udviklere)

Hvis du vil køre programmet direkte fra Python-koden eller ændre i det:

1. Klon repositoriet:
   ```bash
   git clone https://github.com/bosund/DBA-Prisekspert.git
   cd DBA-Prisekspert
   ```
2. Installer kravene (kræver `requests` og `beautifulsoup4`):
   ```bash
   pip install requests beautifulsoup4
   ```
3. Kør GUI'en:
   ```bash
   python dba_gui.py
   ```

*Tip: Du kan også køre scriptet direkte fra terminalen uden GUI via `python scrape_all.py --query "min søgning"`*

## ⚖️ Disclaimer (Vigtigt)

*Dette program er udelukkende udviklet til uddannelsesmæssige (educational) formål og som et personligt projekt.* 

Det er op til brugeren af programmet at overholde gældende lovgivning samt handelsbetingelser (Terms of Service) for de hjemmesider, der interageres med. Forfatteren tager intet ansvar for misbrug, overbelastning af servere eller eventuelle IP-blokeringer forårsaget af brugen af dette værktøj. Brug din sunde fornuft og undlad at scrape enorme mængder sider i træk.
