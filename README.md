# Proxon Control for Home Assistant

[![Open your Home Assistant instance and open this repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Olf1337&repository=ha-proxon-control&category=integration)
[![Add the add-on repository to your Home Assistant.](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FOlf1337%2Fha-proxon-control)

Control and monitor a **Proxon** fresh-air heat/ventilation unit from Home Assistant: operating mode, ventilation level, boost ventilation, room
temperatures (living room in 0.5 °C steps), hot water, CO₂/humidity limits and all readings. You log in with the same **Device ID and password** as in the
Proxon Control phone app.

**Unofficial.** This project is not made, endorsed or supported by Proxon or Nabto. "Proxon" and "Nabto" belong to their owners. It talks to the unit the
same way the phone app does (through Proxon's remote-access server and Nabto's connection library), so it needs an internet connection and may stop working if
those services change. Use at your own risk.

**Not included:** logos, images or texts of the original app, and Nabto's library. The library is downloaded from Nabto's own release on first use
(on Home Assistant OS also some Debian system files, see below). The small helper program that runs the library on Home Assistant OS is in `helper/`, its
source is included.

**Install:** HACS → three-dot menu → *Custom repositories* → `https://github.com/Olf1337/ha-proxon-control` (type *Integration*) → install → restart Home Assistant →
*Settings → Devices & services → Add integration → Proxon Control*.

Works on Linux x86-64 (including Home Assistant OS on Intel/AMD) and macOS on Apple chips. **Not on Raspberry Pi / ARM** (no Nabto library exists for it).

---

# Proxon Control – Integration für Home Assistant

Bringt die Proxon-Anlage (Frischluft-Wärmetechnik) als eigenes Gerät in Home Assistant – mit derselben
Anmeldung wie die App „Proxon Control“: **Device ID + Passwort**.

Danach gibt es in Home Assistant unter *Einstellungen → Geräte & Dienste → Proxon Control* ein Gerät „Proxon“ mit:

| Art | Entitäten |
|---|---|
| Auswahl | Betriebsart (ECO Komfort, Winter, Sommer, Aus; Urlaub wird angezeigt) |
| Zahlen (Schieberegler) | Lüftungsstufe 1–4, Grenzwert CO₂ 400–1500 ppm, Grenzwert Feuchte 0–100 %, Warmwasser 20–55 °C, E-Heizstab 20–70 °C, Soll-Temperatur je Raum (Wohnzimmer 10–30 °C, andere Räume Wohnzimmer ± 3 °C) |
| Schalter | Intensivlüftung, Kühlung, Warmwasser-Wärmepumpe, E-Heizstab, Wärmeelement je Raum |
| Sensoren | Raumtemperaturen, Frisch-/Zu-/Ab-/Fortluft, Warmwasser, Drehzahlen, CO₂, Feuchte, Lüftungsstufe (Ist), Restzeit Intensivlüftung, Restlaufzeit Filter, Betriebsstunden, 4-Wegeventil, Firmware |
| Meldungen | „Filterwechsel bald nötig“, „Kompressor läuft“ |

Die Werte werden alle 10 Sekunden gelesen. Es werden nur die Räume angelegt, die die Anlage als angeschlossen meldet (wie die Raumliste der Proxon-App),
und die Raumnamen stammen aus der Anlage. Welche Räume die Anlage meldet, steht beim ersten Abruf im Home-Assistant-Protokoll („Proxon rooms: …“).

Raumtemperaturen: Das Wohnzimmer lässt sich in 0,5-°C-Schritten einstellen. Die anderen Räume zeigen – wie in der Proxon-App – ihren eigenen Grundwert plus ihren
Versatz; die Anlage speichert den Versatz nur in ganzen Grad, deshalb gehen dort nur ganze Grad (± 3 °C um den Grundwert des Raums).

## Welche Systeme funktionieren?

Die Verbindung zum Proxon-Server läuft (wie in der Original-App) über die Nabto-Bibliothek des Herstellers Nabto.
Diese Bibliothek gibt es nur für **Linux auf Intel/AMD (x86-64)** und **Mac mit Apple-Chip**.

* **Home Assistant OS / Supervised / Container auf Intel- oder AMD-PC (Mini-PC, NUC, VM):** funktioniert direkt.
  Home Assistant läuft dort auf Alpine Linux, in das Nabtos Bibliothek eigentlich nicht passt. Die Integration bringt deshalb ein kleines
  Hilfsprogramm (`bin/proxon-nabto-helper-linux-x86_64`) mit und lädt beim ersten Anmelden die dazu passenden Debian-12-Systemdateien
  (glibc, ca. 5 MB, mit Prüfsumme) und Nabtos Bibliothek herunter. Beides liegt dann unter `/config/proxon_control/`.
* **Home Assistant Core auf Debian/Ubuntu (x86-64):** funktioniert ebenfalls; die Bibliothek wird direkt geladen.
* **Raspberry Pi / ARM:** Für ARM gibt es die Nabto-Bibliothek nicht – die Server-Verbindung funktioniert dort leider nicht.

Das **Proxon-Bridge-Add-on** (Schritt 2) ist nur noch eine Alternative, falls Sie die Verbindung lieber in einem eigenen Add-on laufen lassen möchten.

## Wie wird die Anlage angesprochen?

Wie in der Original-App: **über den Proxon-Server** (Anmeldung mit Device ID und Passwort) und die Fernzugriffs-Technik Nabto. Die Anlage
meldet sich selbst dort an; Home Assistant verbindet sich nicht direkt mit ihr, sondern fragt sie über diese Verbindung ab. Nabto entscheidet dabei
selbst, ob die Daten direkt im Heimnetz oder über seinen Vermittlungsserver laufen. Welchen Weg es bei Ihnen nimmt, kann die Integration derzeit nicht anzeigen.
Ohne Internetverbindung der Anlage oder von Home Assistant geht es deshalb nicht.

## 1. Integration installieren

**Mit HACS:** HACS → oben rechts ⋮ → *Benutzerdefinierte Repositories* → Adresse dieses Repositories, Typ *Integration* → „Proxon Control“ installieren → Home Assistant neu starten.

**Von Hand:** Den Ordner `custom_components/proxon_control` in den Home-Assistant-Konfigurationsordner kopieren
(z. B. über das Samba- oder File-Editor-Add-on), sodass er unter `/config/custom_components/proxon_control` liegt. Home Assistant neu starten.

## 2. Optional: Proxon-Bridge-Add-on (Alternative, nur amd64)

*Einstellungen → Add-ons → Add-on Store → ⋮ → Repositories* → Adresse dieses Repositories hinzufügen →
„Proxon Bridge“ installieren → im Reiter *Konfiguration* **Device ID** und **Passwort** eintragen → starten.
Im Protokoll des Add-ons sollte „logged in to …“ erscheinen. Das Add-on bietet die Werte auf Port 8765 an.

## 3. Einrichten

*Einstellungen → Geräte & Dienste → Integration hinzufügen → „Proxon Control“* und dann:

* **„Am Proxon-Server anmelden“** – Device ID und Passwort eingeben, oder
* **„Über das Proxon-Bridge-Add-on“** (nur wenn Sie das Add-on nutzen) – Adresse `homeassistant.local` (oder die IP von Home Assistant) und Port `8765`.

## Hinweise

* Der Proxon-Server und die Nabto-Bibliothek gehören den jeweiligen Herstellern; ändern diese ihren Dienst, kann die Verbindung ausfallen.
* Das Bridge-Add-on ist im Heimnetz ohne Passwort erreichbar. Wer das nicht möchte, entfernt unter *Add-on → Netzwerk* den Port 8765
  und trägt in der Integration statt `homeassistant.local` den internen Namen des Add-ons ein (steht oben auf der Add-on-Seite als „Hostname“).
* Die Grenze für „Filterwechsel bald nötig“ (30 Tage) ist geschätzt; die Original-App nennt keine feste Grenze.

## Fehlersuche

* „Permission denied“ beim Starten des Hilfsprogramms: Die Integration setzt die nötige Berechtigung jetzt selbst und weicht notfalls auf einen
  temporären Ordner aus, falls Home Assistant in `/config` keine Programme starten lässt.
* Fehlermeldung beim Anmelden: Unter *Einstellungen → System → Protokolle* steht der genaue Grund. Das Hilfsprogramm schreibt zusätzlich
  nach `/config/proxon_control/helper.log`.
* Nach dem Aktualisieren der Dateien Home Assistant neu starten. Heruntergeladene Dateien bleiben erhalten (`/config/proxon_control/`).
  Soll alles neu geladen werden, den Unterordner `runtime` darin über den File-Editor entfernen.
