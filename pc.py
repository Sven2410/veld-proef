"""De pc-kant van de OneDrive-proef: wat de telefoon in OneDrive zette ophalen,
en een klantenlijst neerzetten die de telefoon kan ophalen.

    python pc.py inloggen    # één keer, met een code op microsoft.com/devicelogin
    python pc.py ophalen     # nieuwe rapporten uit OneDrive naar de map ontvangen
    python pc.py klanten     # een proeflijst met klanten naar OneDrive
    python pc.py status      # bij wie, welke OneDrive, en hoe oud het inloggen is

Alleen de standaardbibliotheek van Python. Het inloggen wordt bewaard in
%LOCALAPPDATA%\\onedrive-proef\\inlog.json (op de Mac ~/.local/share), buiten
deze map en dus nooit in git.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

CLIENT_ID = "VUL-HIER-IN"     # hetzelfde als in index.html; geen geheim
SCOPE = "Files.ReadWrite.AppFolder offline_access"
INLOG = "https://login.microsoftonline.com/common/oauth2/v2.0"
GRAPH = "https://graph.microsoft.com/v1.0"
MAP = f"{GRAPH}/me/drive/special/approot"       # Apps/<naam van de app> in OneDrive

HIER = pathlib.Path(__file__).resolve().parent
ONTVANGEN = HIER / "ontvangen"
OPSLAG = pathlib.Path(os.environ.get("LOCALAPPDATA") or pathlib.Path.home() / ".local" / "share") / "onedrive-proef"
INLOGBESTAND = OPSLAG / "inlog.json"

PROEFKLANTEN = [
    {"naam": "Proefklant Jansen", "adres": "Dorpsstraat 1, Ergens"},
    {"naam": "Proefklant De Vries", "adres": "Kerkweg 12, Nergens"},
    {"naam": "Proefklant Bakker", "adres": "Molenlaan 7, Overal"},
]


class Fout(Exception):
    pass


# --- inloggen ---------------------------------------------------------------------

def formulier(url: str, velden: dict) -> dict:
    data = urllib.parse.urlencode(velden).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return json.load(e)


def bewaar_inlog(antwoord: dict, ingelogd: float | None = None) -> dict:
    oud = lees_inlog() or {}
    inlog = {
        "access_token": antwoord["access_token"],
        "refresh_token": antwoord.get("refresh_token") or oud.get("refresh_token"),
        "verloopt": time.time() + int(antwoord.get("expires_in", 3600)),
        "ingelogd": ingelogd or oud.get("ingelogd") or time.time(),
        "vernieuwd": time.time(),
    }
    OPSLAG.mkdir(parents=True, exist_ok=True)
    INLOGBESTAND.write_text(json.dumps(inlog), encoding="utf-8")
    return inlog


def lees_inlog() -> dict | None:
    try:
        return json.loads(INLOGBESTAND.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def inloggen() -> None:
    code = formulier(f"{INLOG}/devicecode", {"client_id": CLIENT_ID, "scope": SCOPE})
    if "device_code" not in code:
        raise Fout(f"Microsoft gaf geen code: {code.get('error_description') or code}")
    print(f"\nGa naar {code['verification_uri']} en vul deze code in: {code['user_code']}\n")
    wacht = int(code.get("interval", 5))
    grens = time.time() + int(code.get("expires_in", 900))
    while time.time() < grens:
        time.sleep(wacht)
        a = formulier(f"{INLOG}/token", {"grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                                         "client_id": CLIENT_ID, "device_code": code["device_code"]})
        if "access_token" in a:
            bewaar_inlog(a, ingelogd=time.time())
            print("Ingelogd.")
            return
        if a.get("error") == "slow_down":
            wacht += 5
        elif a.get("error") != "authorization_pending":
            raise Fout(f"Inloggen lukte niet: {a.get('error_description') or a.get('error')}")
    raise Fout("De code is verlopen. Probeer het opnieuw.")


def toegang() -> str:
    inlog = lees_inlog()
    if not inlog:
        raise Fout("Nog niet ingelogd: python pc.py inloggen")
    if inlog["verloopt"] - time.time() > 120:
        return inlog["access_token"]
    a = formulier(f"{INLOG}/token", {"grant_type": "refresh_token", "client_id": CLIENT_ID,
                                     "refresh_token": inlog["refresh_token"], "scope": SCOPE})
    if "access_token" not in a:
        raise Fout(f"Opnieuw inloggen nodig ({a.get('error')}): python pc.py inloggen")
    return bewaar_inlog(a)["access_token"]


# --- OneDrive -----------------------------------------------------------------------

def onedrive(methode: str, url: str, lijf: bytes | None = None, soort: str = "application/json",
             met_toegang: bool = True) -> tuple[int, bytes]:
    kop = {"Content-Type": soort} if lijf is not None else {}
    if met_toegang:
        kop["Authorization"] = f"Bearer {toegang()}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=lijf, headers=kop, method=methode),
                                    timeout=120) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def json_van(methode: str, url: str, gegevens: dict | None = None) -> tuple[int, dict]:
    status, lijf = onedrive(methode, url, json.dumps(gegevens).encode() if gegevens is not None else None)
    try:
        return status, json.loads(lijf or b"{}")
    except ValueError:
        return status, {}


def map_verwerkt() -> str:
    status, info = json_van("GET", f"{MAP}:/verwerkt")
    if status == 200:
        return info["id"]
    status, info = json_van("POST", f"{MAP}/children",
                            {"name": "verwerkt", "folder": {}, "@microsoft.graph.conflictBehavior": "fail"})
    if status not in (200, 201):
        raise Fout(f"De map verwerkt maken lukte niet: {status} {info}")
    return info["id"]


def ophalen() -> None:
    status, info = json_van("GET", f"{MAP}:/inbox:/children")
    if status == 404:
        print("Er is nog niets binnengekomen.")
        return
    if status != 200:
        raise Fout(f"OneDrive gaf {status}: {info}")
    items = {i["name"]: i for i in info.get("value", [])}
    rapporten = [i for n, i in items.items() if n.endswith(".json")]
    if not rapporten:
        print("Er is niets nieuws.")
        return
    verwerkt = map_verwerkt()
    for item in rapporten:
        status, lijf = onedrive("GET", item["@microsoft.graph.downloadUrl"], met_toegang=False)
        if status != 200:
            print(f"  {item['name']}: ophalen lukte niet ({status})")
            continue
        rapport = json.loads(lijf)
        doel = ONTVANGEN / f"{rapport['gemaakt'][:10]} {veilig(rapport['klant'])} {rapport['id'][:8]}"
        doel.mkdir(parents=True, exist_ok=True)
        (doel / "rapport.json").write_bytes(lijf)
        mee = [item]
        foto = items.get(rapport.get("foto") or "")
        if foto:
            status, beeld = onedrive("GET", foto["@microsoft.graph.downloadUrl"], met_toegang=False)
            if status == 200:
                (doel / "foto.jpg").write_bytes(beeld)
                mee.append(foto)
        for i in mee:
            json_van("PATCH", f"{GRAPH}/me/drive/items/{i['id']}", {"parentReference": {"id": verwerkt}})
        onderweg = tijdsverschil(rapport["gemaakt"], rapport.get("verstuurd"))
        print(f"  {rapport['klant']}: {rapport.get('opmerking') or '(geen opmerking)'}"
              f"{' + foto' if len(mee) > 1 else ''}; gemaakt {rapport['gemaakt'][:16].replace('T', ' ')} UTC,"
              f" verstuurd {onderweg} later. Staat in {doel.relative_to(HIER)}")


def klanten() -> None:
    status, lijf = onedrive("PUT", f"{MAP}:/klanten.json:/content",
                            json.dumps(PROEFKLANTEN, ensure_ascii=False, indent=1).encode())
    if status not in (200, 201):
        raise Fout(f"Neerzetten lukte niet: {status} {lijf[:200]!r}")
    print(f"{len(PROEFKLANTEN)} proefklanten staan in OneDrive. Op de telefoon: Klanten ophalen.")


def status() -> None:
    inlog = lees_inlog()
    if not inlog:
        print("Nog niet ingelogd: python pc.py inloggen")
        return
    print(f"Ingelogd {(time.time() - inlog['ingelogd']) / 3600:.1f} uur geleden,"
          f" laatst vernieuwd {(time.time() - inlog['vernieuwd']) / 3600:.1f} uur geleden.")
    s, info = json_van("GET", MAP)
    if s != 200:
        raise Fout(f"OneDrive gaf {s}: {info}")
    soort = {"personal": "persoonlijk", "business": "zakelijk"}.get(
        info.get("parentReference", {}).get("driveType"), "onbekend")
    print(f"Map in OneDrive ({soort}): {info.get('webUrl')}")


def veilig(naam: str) -> str:
    return "".join(c for c in naam if c.isalnum() or c in " -_").strip()[:40] or "klant"


def tijdsverschil(van: str, tot: str | None) -> str:
    if not tot:
        return "?"
    from datetime import datetime
    s = (datetime.fromisoformat(tot.replace("Z", "+00:00")) - datetime.fromisoformat(van.replace("Z", "+00:00")))
    s = s.total_seconds()
    return f"{s / 3600:.1f} uur" if s >= 3600 else f"{s / 60:.0f} minuten"


if __name__ == "__main__":
    opdrachten = {"inloggen": inloggen, "ophalen": ophalen, "klanten": klanten, "status": status}
    keuze = sys.argv[1] if len(sys.argv) > 1 else ""
    if keuze not in opdrachten:
        print(__doc__)
        sys.exit(1)
    if CLIENT_ID.startswith("VUL"):
        print("Vul eerst CLIENT_ID in, bovenin pc.py.")
        sys.exit(1)
    try:
        opdrachten[keuze]()
    except Fout as e:
        print(e)
        sys.exit(1)
