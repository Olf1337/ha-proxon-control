# Proxon Control for Home Assistant

[![Open your Home Assistant instance and open this repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Olf1337&repository=ha-proxon-control&category=integration)
[![Add the add-on repository to your Home Assistant.](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FOlf1337%2Fha-proxon-control)
[![Buy me a coffee / Spendier mir einen Kaffee](https://img.shields.io/badge/Buy%20me%20a%20coffee-PayPal-00457C?logo=paypal&logoColor=white)](https://www.paypal.com/paypalme/olf1337)

Control and monitor a **Proxon** fresh-air heat/ventilation unit from Home Assistant: every connected room as its own thermostat, operating mode,
ventilation level, boost ventilation, hot water, CO₂/humidity limits and all readings. You log in with the same **Device ID and password** as in the
Proxon Control phone app. Every change is read back from the unit, and the polling interval is adjustable (5–3600 s).

**Works from outside your home network.** It uses the same remote access as the phone app, so no VPN or port forwarding is needed – Home Assistant and the
unit only need internet access, and they don't have to be in the same network.

**Unofficial.** This project is not made, endorsed or supported by Proxon or Nabto. "Proxon" and "Nabto" belong to their owners. It talks to the unit the
same way the phone app does (through Proxon's remote-access server and Nabto's connection library), so it needs an internet connection and may stop working if
those services change. Use at your own risk.

**Not included:** logos, images or texts of the original app, and Nabto's library. The library is downloaded from Nabto's own release on first use
(on Home Assistant OS also some Debian system files, see below). The small helper program that runs the library on Home Assistant OS is in `helper/`, its
source is included.

**Install:** HACS → three-dot menu → *Custom repositories* → `https://github.com/Olf1337/ha-proxon-control` (type *Integration*) → install → restart Home Assistant →
*Settings → Devices & services → Add integration → Proxon Control*.

Works on Linux x86-64 (including Home Assistant OS on Intel/AMD) and macOS on Apple chips. **Not on Raspberry Pi / ARM** (no Nabto library exists for it).

**Upgrading from 0.1.x:** rooms are now thermostats (`climate` entities). The old room numbers and switches are removed on start; update automations and dashboards that used them.

---

# Proxon Control – Integration für Home Assistant (Version 0.2.0)

Bringt die Proxon-Anlage (Frischluft-Wärmetechnik) als eigenes Gerät in Home Assistant – mit derselben
Anmeldung wie die App „Proxon Control“: **Device ID + Passwort**.

> ### Funktioniert auch von außerhalb des Heimnetzes
> Die Integration spricht die Anlage über denselben Fernzugriff an wie die Proxon-App (Proxon-Server und Nabto-Verbindung). Dafür braucht es **kein VPN,
> keine Portfreigabe und keine feste Adresse im Heimnetz**: Anlage und Home Assistant brauchen nur Internet. Home Assistant kann also an einem ganz anderen
> Ort laufen als die Anlage (z. B. Home Assistant in der Wohnung, Anlage im Ferienhaus), und auch eine Verbindung aus dem Mobilfunknetz genügt.
> Das unterscheidet sie von Integrationen, die die Anlage nur im lokalen Netz erreichen. Umgekehrt gilt: ohne Internet geht es nicht.

Danach gibt es in Home Assistant unter *Einstellungen → Geräte & Dienste → Proxon Control* ein Gerät „Proxon“ mit:

| Art | Entitäten |
|---|---|
| Thermostate | **Jeder angeschlossene Raum als eigenes Thermostat**: Ist- und Soll-Temperatur, Wärmeelement an/aus, „heizt gerade“. Wohnzimmer 10–30 °C in 0,5-°C-Schritten, andere Räume 14–26 °C in ganzen Grad (± 3 °C um den eigenen Grundwert des Raums) |
| Auswahl | Betriebsart (ECO Komfort, Winter, Sommer, Aus; Urlaub wird angezeigt) |
| Zahlen (Schieberegler) | Lüftungsstufe 1–4, Grenzwert CO₂ 400–1500 ppm (nur mit CO₂-Sensor), Grenzwert Feuchte 0–100 %, Warmwasser 20–55 °C, E-Heizstab 20–70 °C |
| Schalter | Intensivlüftung, Kühlung, Warmwasser-Wärmepumpe, E-Heizstab |
| Sensoren | Raumtemperaturen, Frisch-/Zu-/Ab-/Fortluft, Warmwasser, Drehzahlen, CO₂, Feuchte, Lüftungsstufe (Ist), Restzeit Intensivlüftung, Restlaufzeit Filter, Betriebsstunden, 4-Wegeventil, Firmware |
| Meldungen | „Filterwechsel bald nötig“, „Kompressor läuft“ |

## Neu in Version 0.2.0

* **Räume als eigene Thermostate.** Jeder Raum ist jetzt ein Thermostat (statt einer Zahl plus einem Schalter) – das passt zu den Home-Assistant-Karten und
  Automationen für Heizung. Das Wärmeelement des Raums ist der Thermostat-Modus „Heizen“/„Aus“. Die alten Raum-Zahlen und Raum-Schalter aus Version 0.1 werden beim
  Start automatisch entfernt; Automationen oder Dashboards, die sie benutzt haben, müssen auf das Thermostat umgestellt werden.
* **Schreiben mit Zurücklesen.** Nach jeder Änderung liest die Integration den Wert von der Anlage zurück (bis zu dreimal, falls sie einen Moment braucht) und
  zeigt erst dann „geändert“. Übernimmt die Anlage einen Wert nicht, kommt eine Fehlermeldung („Die Anlage hat … nicht übernommen: gewünscht …, sie meldet …“),
  und die Anzeige zeigt den Wert, den die Anlage wirklich hat – nicht den gewünschten.
* **Einstellbares Abfrageintervall.** Unter *Geräte & Dienste → Proxon Control → Konfigurieren* lässt sich einstellen, wie oft die Anlage abgefragt wird
  (5 bis 3600 Sekunden, Standard 10). Beim Bridge-Add-on gibt es dieselbe Einstellung („poll_seconds“).

## Hinweise zu den Werten

Die Werte werden im eingestellten Intervall (Standard alle 10 Sekunden) gelesen. Es werden nur die Räume angelegt, die die Anlage als angeschlossen meldet
(wie die Raumliste der Proxon-App), und die Raumnamen stammen aus der Anlage. Welche Räume die Anlage meldet, steht beim ersten Abruf im
Home-Assistant-Protokoll („Proxon rooms: …“).

Raumtemperaturen: Das Wohnzimmer wird in hundertstel Grad gespeichert und lässt sich deshalb in 0,5-°C-Schritten einstellen. Die anderen Räume zeigen – wie in der
Proxon-App – ihren eigenen Grundwert plus ihren Versatz; die Anlage speichert den Versatz nur in ganzen Grad, deshalb gehen dort nur ganze Grad.

**Getestet mit Home Assistant 2026.2.3 und 2026.11.1** (jeweils gegen eine nachgebildete Anlage, nicht gegen eine echte; die Testhilfen für 2026.11 sind noch nicht
offiziell erschienen, deshalb lief der Test dort mit einer kleinen Anpassung der Testumgebung, nicht des Programms). Ältere Versionen sind nicht geprüft.

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
Ohne Internetverbindung der Anlage oder von Home Assistant geht es deshalb nicht. Genau deshalb funktioniert die Integration auch von außerhalb des Heimnetzes
(siehe oben). Der Fernzugriff ist dabei derselbe Weg wie in der Proxon-App; ich habe ihn in dieser Entwicklungsumgebung allerdings nicht an einer echten Anlage
in einem fremden Netz ausprobiert.

## 1. Integration installieren

**Mit HACS:** HACS → oben rechts ⋮ → *Benutzerdefinierte Repositories* → Adresse dieses Repositories, Typ *Integration* → „Proxon Control“ installieren → Home Assistant neu starten.
Ab Home Assistant 2026.11 ist HACS fest eingebaut und heißt *Einstellungen → Marketplace*; das Hinzufügen eines eigenen Repositories (Menü oben rechts, „Benutzerdefinierte Repositories“ / „Custom repositories“) läuft dort entsprechend.

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

## Support / Unterstützen

If this integration is useful to you, you can buy me a coffee. / Wenn dir die Integration gefällt, kannst du mir gerne einen Kaffee spendieren.

[![Buy me a coffee via PayPal](https://img.shields.io/badge/Buy%20me%20a%20coffee-PayPal-00457C?logo=paypal&logoColor=white&style=for-the-badge)](https://www.paypal.com/paypalme/olf1337)
