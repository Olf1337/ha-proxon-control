# Proxon Control for Home Assistant

[![Open your Home Assistant instance and open this repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Olf1337&repository=ha-proxon-control&category=integration)
[![Add the add-on repository to your Home Assistant.](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FOlf1337%2Fha-proxon-control)
[![Buy me a coffee / Spendier mir einen Kaffee](https://img.shields.io/badge/Buy%20me%20a%20coffee-PayPal-00457C?logo=paypal&logoColor=white)](https://www.paypal.com/paypalme/olf1337)

Control and monitor a **Proxon** fresh-air heat/ventilation unit from Home Assistant: every connected room as its own thermostat, the ventilation as a fan (level 1–4, boost as preset),
hot water as a water heater, **hot water as a store for solar surplus and cheap electricity**, **summer night cooling**, a **hot-water boost** with the immersion heater, an **animated dashboard** (unit, hot water, house), the weekly ventilation schedule (view and edit), operating mode, CO₂/humidity limits and all readings. You log in with the same **Device ID and password** as in the
Proxon Control phone app. Every change is read back from the unit, and the polling interval is adjustable (5–3600 s). A diagnostics download helps with support.

**Home network first, cloud as fallback (new in 0.8.0).** Home Assistant talks to the unit directly in your home network (UDP port 5570, plain Python,
fast, keeps working when the internet is down) and falls back to Proxon's remote-access server when the unit can't be reached there. You can also choose
*home network only* or *Proxon server only*. A certificate is fetched once from the Proxon portal with your Device ID and password; after that the home
network connection needs no internet. Through the Proxon server it also works from elsewhere (no VPN or port forwarding needed).

**Unofficial.** This project is not made, endorsed or supported by Proxon or Nabto. "Proxon" and "Nabto" belong to their owners. It talks to the unit the
same ways the phone app does (in the home network, or through Proxon's remote-access server and Nabto's connection library), and may stop working if
those change. Use at your own risk. The home network protocol follows the [ha-lan-proxon](https://github.com/Fummy1990/ha-lan-proxon) project (MIT, see
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)).

**Not included:** logos, images or texts of the original app, and Nabto's library. The library is downloaded from Nabto's own release on first use
(on Home Assistant OS also some Debian system files, see below). The small helper program that runs the library on Home Assistant OS is in `helper/`, its
source is included.

**Install:** HACS → three-dot menu → *Custom repositories* → `https://github.com/Olf1337/ha-proxon-control` (type *Integration*) → install → restart Home Assistant →
*Settings → Devices & services → Add integration → Proxon Control*.

**Raspberry Pi / ARM: supported from 0.8.0** over the home network (Home Assistant and the unit in the same network). The Proxon server fallback needs
Nabto's library, which only exists for Linux x86-64 (including Home Assistant OS on Intel/AMD) and macOS on Apple chips. The Proxon Bridge is no longer
needed on a Raspberry Pi; it stays for special cases (e.g. Home Assistant in a different network than the unit, on ARM).

**What's new:** see [CHANGELOG.md](CHANGELOG.md).

---

# Proxon Control – Integration für Home Assistant

Bringt die Proxon-Anlage (Frischluft-Wärmetechnik) als eigenes Gerät in Home Assistant – mit derselben
Anmeldung wie die App „Proxon Control“: **Device ID + Passwort**.

> ### Heimnetz zuerst, Proxon-Server als Ausweichweg (neu in 0.8.0)
> Die Integration spricht die Anlage **direkt im Heimnetz** an (schnell, funktioniert auch ohne Internet, auch auf dem **Raspberry Pi**). Ist sie dort
> nicht erreichbar, nimmt sie automatisch den **Proxon-Server** – denselben Fernzugriff wie die Proxon-App. Damit funktioniert sie weiterhin auch von außerhalb
> des Heimnetzes, ohne VPN und Portfreigabe. Wer möchte, stellt „Nur Heimnetz“ oder „Nur Proxon-Server“ ein.

Danach gibt es in Home Assistant unter *Einstellungen → Geräte & Dienste → Proxon Control* ein Gerät „Proxon“ mit:

| Art | Entitäten |
|---|---|
| Thermostate | **Jeder angeschlossene Raum als eigenes Gerät mit Thermostat und Temperatur** (einem Bereich zuordenbar) (bis zu 20 Nebenräume, wie die Anlage sie meldet): Ist- und Soll-Temperatur, Modus „Wärmeelement aus“ oder „Wärmeelement freigegeben“, Sensor „Wärmeelement“ (nicht freigegeben / bereit / heizt), und was die Anlage gerade macht (Heizen / Kühlen / Lüften). Wohnzimmer 10–30 °C in 0,5-°C-Schritten, andere Räume 14–26 °C in ganzen Grad (± 3 °C um den eigenen Grundwert des Raums) |
| Lüftung | **Als Ventilator**: Stufe 1–4 als Geschwindigkeit (25/50/75/100 %), Intensivlüftung als Voreinstellung „Intensivlüftung“. Passt zu den Ventilator-Karten und zu Sprachassistenten. Ausschalten geht nur über die Betriebsart „Aus“ (das würde die ganze Anlage ausschalten) |
| Warmwasser | **Als Warmwasserbereiter**: Ist- und Soll-Temperatur (20–55 °C) und Betriebsart Aus / Wärmepumpe / Wärmepumpe + E-Heizstab / nur E-Heizstab (nur mit Warmwasser-Wärmepumpe T300) |
| Wochenprogramm | **Lüftungs-Zeitprogramm der Anlage**: je Wochentag ein Sensor („06:00–08:00 Stufe 2 · 17:00–22:00 Stufe 3“, die drei Phasen als Attribute), „Zeitprogramm aktiv“, Uhr der Anlage. Bearbeiten direkt in den Geräten „Proxon Zeitprogramm Montag“ … „Sonntag“ (je Phase Beginn, Ende, Lüftungsstufe), Knöpfe „Montag → Di–Fr / alle Tage“, oder über die Aktionen *Zeitprogramm-Phase setzen* und *Zeitprogramm-Tag kopieren* |
| Auswahl | Betriebsart (ECO Komfort, Winter, Sommer, Ofenbetrieb, Aus; Urlaub wird angezeigt) |
| Zahlen | Lüftungsstufe 1–4, Grenzwert CO₂ 400–1500 ppm (nur mit CO₂-Sensor), Grenzwert Feuchte 0–100 %, Warmwasser 20–55 °C, E-Heizstab 20–70 °C, Dauer der Intensivlüftung |
| Schalter | Intensivlüftung, Kühlung, Warmwasser-Wärmepumpe, E-Heizstab, Legionellenschaltung, Legionellenschutz mit Sonne / planen (mit Tag und Uhrzeit), Wärmeelemente aller Räume |
| Sensoren | Raumtemperaturen, Innen (Mittel aller Räume), Frisch-/Zu-/Ab-/Fortluft, Warmwasser, Drehzahlen, CO₂, Feuchte, Lüftungsstufe (Ist), Restzeit Intensivlüftung, Restlaufzeit Filter (nach der an der Anlage eingestellten Standzeit), Betriebsstunden, 4-Wegeventil, Firmware, Warmwasser unten, Warmwasser-Ladezustand, Duschvorrat, Aktueller Betrieb, Wärmerückgewinnung, Stromkosten (mit Preis-Sensor) |
| Meldungen | „Filterwechsel bald nötig“, „Kompressor läuft“, „Störung“ (Fehlerwörter der Anlage als Attribute), Bypass, Erdwärmetauscher, PV-Eingang; Filterwechsel, Störung und eine falsch gehende Anlagenuhr erscheinen zusätzlich unter *Einstellungen → Reparaturen*, ebenso eine Woche ohne 60 °C im Warmwasser ohne Legionellenschutz |
| Urlaubsmodus | Schalter: Lüftung Stufe 1, Wohnzimmer 18 °C, übrige Räume −3 °C, Wärmeelemente aus, Warmwasser aus – beim Ausschalten werden die vorherigen Werte wiederhergestellt. Dazu ein Urlaubsplan mit Abreise und Rückkehr, der ihn selbst ein- und rechtzeitig vor der Rückkehr ausschaltet |
| Diagnose | Antwortzeit der Anlage, Verbindungsweg (Heimnetz / direkt über das Internet / über Vermittlungsserver; im Heimnetz exakt, über den Proxon-Server geschätzt), Uhr der Anlage und ihre Abweichung, Firmware (auch des Warmwasser-Moduls), Betriebsstunden, letzter Schreibfehler, Temperaturen, Druck und Ventile des Kältekreises |

**Was neu ist:** in [CHANGELOG.md](CHANGELOG.md) (und in den Release-Hinweisen auf GitHub).

## Die Seite „Proxon“

In der Seitenleiste erscheint die Seite **„Proxon“**, im Liquid-Glass-Look und für Handy, Tablet und Computer:

* **Zuhause:** die Anlage im Schnitt (Frisch-, Zu-, Ab- und Fortluft mit Temperaturen, Lüfter mit Drehzahl, Wärmepumpe), der Warmwasserspeicher
  (warmes Wasser in Litern, Duschminuten, Temperaturen) und jeder Raum als Kachel. Eingeschaltete Funktionen (Urlaub, Legionellenschutz,
  PV-Überschuss, Sommer/Winter …) stehen als kleine Kapseln in der Statuszeile; ein Tipp öffnet ihre Einstellung.
* **Einstellungen:** links die Bereiche (Lüftung, Wochenprogramm, Urlaub, Warmwasser, Automatiken, Nachtabsenkung) mit Kurzinfo, rechts der
  gewählte Bereich; auf dem Handy erst die Liste, dann der Bereich.
* **Sollwerte nur mit − und +** (gedrückt halten wiederholt): Wischen beim Scrollen verstellt nichts.

Das frühere fertige Dashboard „Proxon Control“ (Aktion *Dashboard erstellen*) ist **abgekündigt**: Es funktioniert bis Version 2.0
weiter, danach entfällt es. Solange es existiert, steht ein Hinweis unter *Einstellungen → Reparaturen*.

## Bekannte Grenzen

* Die **Uhr der Anlage** lässt sich nicht stellen – die Anlage lehnt das Schreiben übers Netz ab (in der Proxon-App geht es).
* Der Ausweichweg über den **Proxon-Server** braucht Nabtos Bibliothek, die es nur für Linux auf Intel/AMD und Mac mit Apple-Chip gibt
  (Raspberry Pi: nur Heimnetz).
* **Eine Anlage pro Home Assistant.** Eine zweite lässt sich nicht hinzufügen; mehrere Anlagen kommen frühestens in einem
  späteren Release.
* Grenzwert CO₂ wirkt nur mit CO₂-Fühler; Grenzwert CO₂ und Feuchte steuern die Lüftung nur im ECO-Komfortbetrieb.

## Hinweise zu den Werten

Die Werte werden im eingestellten Intervall (Standard alle 10 Sekunden) gelesen. Es werden nur die Räume angelegt, die die Anlage als angeschlossen meldet
(wie die Raumliste der Proxon-App), und die Raumnamen stammen aus der Anlage. Welche Räume die Anlage meldet, steht beim ersten Abruf im
Home-Assistant-Protokoll („Proxon rooms: …“).

Raumtemperaturen: Das Wohnzimmer wird in hundertstel Grad gespeichert und lässt sich deshalb in 0,5-°C-Schritten einstellen. Die anderen Räume zeigen – wie in der
Proxon-App – ihren eigenen Grundwert plus ihren Versatz; die Anlage speichert den Versatz nur in ganzen Grad, deshalb gehen dort nur ganze Grad.

**Voraussetzung: Home Assistant 2026.3 oder neuer.** Die automatischen Tests laufen bei jeder Änderung mit dem aktuellen Home Assistant gegen eine
nachgebildete Anlage; im Alltag läuft die Integration mit Home Assistant 2026.11 an einer echten Anlage.

## Welche Systeme funktionieren?

* **Heimnetz-Verbindung: überall**, auch auf **Raspberry Pi / ARM**. Voraussetzung: Home Assistant und die Anlage sind im selben Netz (bzw. die Anlage ist
  per IP-Adresse erreichbar, UDP-Port 5570).
* **Proxon-Server (Ausweichweg)** läuft – wie in der Original-App – über die Nabto-Bibliothek. Diese gibt es nur für **Linux auf Intel/AMD (x86-64)** und
  **Mac mit Apple-Chip**:
  * **Home Assistant OS / Supervised / Container auf Intel- oder AMD-PC:** Home Assistant läuft dort auf Alpine Linux, in das Nabtos Bibliothek eigentlich
    nicht passt. Die Integration bringt deshalb ein kleines Hilfsprogramm (`bin/proxon-nabto-helper-linux-x86_64`) mit und lädt bei der ersten Verbindung
    über den Proxon-Server die passenden Debian-12-Systemdateien (glibc, ca. 5 MB, mit Prüfsumme) und Nabtos Bibliothek herunter (`/config/proxon_control/`).
  * **Home Assistant Core auf Debian/Ubuntu (x86-64):** die Bibliothek wird direkt geladen.
  * **Raspberry Pi / ARM:** Hier gibt es keinen Ausweichweg über den Proxon-Server; die Integration nutzt nur das Heimnetz.

Die **Proxon-Bridge** (Add-on oder Docker-Container) ist nur noch für Sonderfälle gedacht, z. B. Home Assistant auf ARM in einem anderen Netz als die Anlage.

## Wie wird die Anlage angesprochen?

* **Im Heimnetz:** Home Assistant sucht die Anlage per Broadcast (oder nimmt die eingetragene IP-Adresse) und spricht sie direkt über UDP-Port 5570 an –
  so wie die Proxon-App, wenn das Handy im selben WLAN ist. Die Anlage nimmt nur Verbindungen mit einem vom Proxon-Portal unterschriebenen Zertifikat an;
  dieses holt die Integration einmalig. **Hinweis:** Die Daten laufen im Heimnetz unverschlüsselt (so arbeitet die Anlage lokal) – also nur in einem
  vertrauenswürdigen Netz verwenden.
* **Über den Proxon-Server:** Anmeldung mit Device ID und Passwort und die Fernzugriffs-Technik Nabto, wie in der Original-App. Die Anlage meldet sich selbst
  dort an; das funktioniert auch von außerhalb des Heimnetzes. Nabto entscheidet dabei selbst, ob die Daten direkt oder über seinen Vermittlungsserver laufen;
  der Diagnose-Sensor „Verbindungsweg“ schätzt das aus der Antwortzeit.

Welcher Weg gerade genutzt wird, zeigt das Attribut `via` des Sensors „Verbindungsweg“ (`local` oder `cloud`). Wechsel stehen im Protokoll.

## 1. Integration installieren

**Mit HACS:** HACS → oben rechts ⋮ → *Benutzerdefinierte Repositories* → Adresse dieses Repositories, Typ *Integration* → „Proxon Control“ installieren → Home Assistant neu starten.
Ab Home Assistant 2026.11 ist HACS fest eingebaut und heißt *Einstellungen → Marketplace*; das Hinzufügen eines eigenen Repositories (Menü oben rechts, „Benutzerdefinierte Repositories“ / „Custom repositories“) läuft dort entsprechend.

**Von Hand:** Den Ordner `custom_components/proxon_control` in den Home-Assistant-Konfigurationsordner kopieren
(z. B. über das Samba- oder File-Editor-Add-on), sodass er unter `/config/custom_components/proxon_control` liegt. Home Assistant neu starten.

## Sonderfall: Bridge auf einem anderen Rechner

Ab 0.8.0 braucht der Raspberry Pi keine Bridge mehr. Nur wenn Home Assistant auf ARM läuft **und** die Anlage nicht im selben Netz ist, kann die Verbindung
über die Proxon-Bridge auf einem x86-64-Rechner laufen (NAS mit Intel/AMD-Prozessor, Mini-PC, Server) mit Docker:

1. [`proxon_bridge/docker-compose.yml`](proxon_bridge/docker-compose.yml) in einen leeren Ordner auf diesem Rechner legen, Device ID, Passwort und einen
   langen, zufälligen **Zugriffsschlüssel** eintragen.
2. `docker compose up -d` – im Log sollte „logged in to …“ erscheinen.
3. In Home Assistant: *Integration hinzufügen → Proxon Control → „Über das Proxon-Bridge-Add-on“* – Adresse des Rechners, Port `8765` und derselbe Zugriffsschlüssel.

Ohne Zugriffsschlüssel kann jeder im Heimnetz die Anlage über die Bridge steuern – deshalb bitte immer einen setzen. Das gilt auch für das Add-on (Option „token“).

## 2. Optional: Proxon-Bridge-Add-on (Alternative, nur amd64)

*Einstellungen → Add-ons → Add-on Store → ⋮ → Repositories* → Adresse dieses Repositories hinzufügen →
„Proxon Bridge“ installieren → im Reiter *Konfiguration* **Device ID** und **Passwort** eintragen → starten.
Im Protokoll des Add-ons sollte „logged in to …“ erscheinen. Das Add-on bietet die Werte auf Port 8765 an.

## 3. Einrichten

*Einstellungen → Geräte & Dienste → Integration hinzufügen → „Proxon Control“* und dann:

* **„Mit Device ID + Passwort anmelden“** – Device ID und Passwort eingeben, Verbindung wählen (Standard: „Heimnetz zuerst“), optional die IP-Adresse der
  Anlage. Auf dem Raspberry Pi entfällt die Auswahl (nur Heimnetz). Oder
* **„Über das Proxon-Bridge-Add-on“** (nur wenn Sie das Add-on nutzen) – Adresse `homeassistant.local` (oder die IP von Home Assistant) und Port `8765`.

## Hinweise

* Der Proxon-Server und die Nabto-Bibliothek gehören den jeweiligen Herstellern; ändern diese ihren Dienst, kann die Verbindung über den Server ausfallen.
  Die Heimnetz-Verbindung braucht nach dem einmaligen Zertifikat keinen Dienst mehr.
* Im Heimnetz sind die Daten unverschlüsselt (wie bei der Anlage üblich). Die Anlage erlaubt pro Sitzung nur eine begrenzte Zahl von Abfragen; die
  Integration öffnet für jede Abfrage eine eigene Sitzung und schließt sie danach wieder.
* Das Bridge-Add-on ist im Heimnetz ohne Passwort erreichbar. Wer das nicht möchte, entfernt unter *Add-on → Netzwerk* den Port 8765
  und trägt in der Integration statt `homeassistant.local` den internen Namen des Add-ons ein (steht oben auf der Add-on-Seite als „Hostname“).
* Änderungen am Warmwasser (Temperatur, Wärmepumpe, E-Heizstab) übernimmt das Warmwasser-Modul der Anlage langsam. Die Integration wartet darauf bis zu
  einer Minute (Wärmepumpe an/aus bis zu 1,5 Minuten) und schickt den Wert zwischendurch noch zweimal. So lange dreht sich in Home Assistant der Ladekreis.
* Die Grenze für „Filterwechsel bald nötig“ (30 Tage) ist geschätzt; die Original-App nennt keine feste Grenze.

## Fehlersuche

* „Die Anlage hat im Heimnetz nicht geantwortet“: Ist Home Assistant im selben Netz? Hilft eine feste IP-Adresse der Anlage im Router, die unter
  *Konfigurieren* eingetragen wird? UDP-Port 5570 darf nicht von einer Firewall/VLAN-Regel blockiert sein. Wird das Zertifikat abgelehnt, holt die
  Integration beim nächsten Versuch automatisch ein neues; die Anlage muss dafür einmal online gewesen sein.
* Home Assistant in **Docker Desktop unter Windows (oder macOS)**: Die automatische Suche per Broadcast erreicht die Anlage dort nicht (die Broadcasts
  kommen nicht durch das Netz von Docker Desktop). Die IP-Adresse der Anlage unter *Konfigurieren* eintragen, dann klappt die Verbindung.

* „Permission denied“ beim Starten des Hilfsprogramms: Die Integration setzt die nötige Berechtigung jetzt selbst und weicht notfalls auf einen
  temporären Ordner aus, falls Home Assistant in `/config` keine Programme starten lässt.
* Fehlermeldung beim Anmelden: Unter *Einstellungen → System → Protokolle* steht der genaue Grund. Das Hilfsprogramm schreibt zusätzlich
  nach `/config/proxon_control/helper.log`.
* Nach dem Aktualisieren der Dateien Home Assistant neu starten. Heruntergeladene Dateien bleiben erhalten (`/config/proxon_control/`).
  Soll alles neu geladen werden, den Unterordner `runtime` darin über den File-Editor entfernen.

## Support / Unterstützen

If this integration is useful to you, you can buy me a coffee. / Wenn dir die Integration gefällt, kannst du mir gerne einen Kaffee spendieren.

[![Buy me a coffee via PayPal](https://img.shields.io/badge/Buy%20me%20a%20coffee-PayPal-00457C?logo=paypal&logoColor=white&style=for-the-badge)](https://www.paypal.com/paypalme/olf1337)
