// Wat de telefoon en de pc allebei nodig hebben: de koppeling en het
// versleutelen.
//
// De koppelcode is "<id van de pc>.<sleutel>" en staat in de QR-code op de
// pc. Alles wat over de verbinding gaat is met die sleutel versleuteld
// (AES-GCM), bovenop wat WebRTC zelf al versleutelt. Zo kan ook het
// makelaartje dat telefoon en pc in contact brengt, of een doorgeefserver als
// een directe verbinding niet lukt, niets lezen, zelfs niet als het kwaad wil.

const b64 = {
  naar: (buf) => btoa(String.fromCharCode(...new Uint8Array(buf)))
    .replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, ""),
  van: (s) => Uint8Array.from(atob(s.replace(/-/g, "+").replace(/_/g, "/")), (c) => c.charCodeAt(0)),
};

const tekst = {
  naar: (o) => new TextEncoder().encode(JSON.stringify(o)),
  van: (buf) => JSON.parse(new TextDecoder().decode(buf)),
};

function nieuweKoppelcode() {
  const letters = "abcdefghijkmnpqrstuvwxyz23456789";
  const id = Array.from(crypto.getRandomValues(new Uint8Array(20)), (b) => letters[b % letters.length]).join("");
  return `veldproef-${id}.${b64.naar(crypto.getRandomValues(new Uint8Array(32)))}`;
}

function leesKoppelcode(code) {
  const m = /^(veldproef-[a-z0-9]{20})\.([A-Za-z0-9_-]{43})$/.exec(String(code || "").trim());
  return m ? { code: m[0], pc: m[1], sleutel: m[2] } : null;
}

const maakSleutel = (s) => crypto.subtle.importKey("raw", b64.van(s), "AES-GCM", false, ["encrypt", "decrypt"]);

async function versleutel(sleutel, bytes) {
  const iv = crypto.getRandomValues(new Uint8Array(12));
  return { iv: b64.naar(iv), data: await crypto.subtle.encrypt({ name: "AES-GCM", iv }, sleutel, bytes) };
}

// Alleen STUN: daarmee vinden telefoon en pc elkaar als hun netwerken dat
// toelaten. De doorgeefservers (TURN) die PeerJS zelf meegeeft bestaan niet
// meer (08-10-2026: geen adres), en wachten daarop maakte het alleen trager.
// Achter 4G lukt een directe verbinding vaak niet; daarvoor is een eigen
// doorgeefserver nodig.
const VERBINDING = { config: { iceServers: [
  { urls: "stun:stun.cloudflare.com:3478" },
  { urls: "stun:stun.l.google.com:19302" },
] }, debug: 0 };

const ontsleutel = (sleutel, { iv, data }) => crypto.subtle.decrypt({ name: "AES-GCM", iv: b64.van(iv) }, sleutel, data);

// Wacht op een bericht dat aan past voldoet, hooguit ms milliseconden.
function wachtOp(conn, past, ms, anders) {
  return new Promise((ok, nee) => {
    const h = (m) => {
      if (!past(m)) return;
      clearTimeout(t);
      conn.off("data", h);
      ok(m);
    };
    const t = setTimeout(() => { conn.off("data", h); nee(new Error(anders)); }, ms);
    conn.on("data", h);
  });
}

// --- logboek, voor allebei ------------------------------------------------------

const $ = (s) => document.querySelector(s);
const tijd = (t) => new Date(t).toLocaleString("nl-NL", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", second: "2-digit" });

function maakLogboek(sleutel, lijst) {
  const toon = () => {
    const l = JSON.parse(localStorage.getItem(sleutel) || "[]");
    lijst.replaceChildren(...l.slice(0, 60).map((r) => {
      const li = document.createElement("li");
      if (r.fout) li.className = "fout";
      const t = document.createElement("span");
      t.className = "tijd";
      t.textContent = tijd(r.t);
      li.append(t, r.tekst);
      return li;
    }));
  };
  const log = (tekst, fout = false) => {
    const l = JSON.parse(localStorage.getItem(sleutel) || "[]");
    l.unshift({ t: Date.now(), tekst, fout });
    localStorage.setItem(sleutel, JSON.stringify(l.slice(0, 300)));
    toon();
  };
  toon();
  return log;
}
