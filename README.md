# Veld-proef

Een proef voor een boekhoudprogramma op Windows met een veld-app op de
telefoon: een rapport offline invullen op de telefoon, en het **rechtstreeks**
naar de pc sturen, zonder account, zonder eigen server die gegevens bewaart,
en zonder certificaat op de telefoon.

- `index.html`: de telefoon. Koppelen met een QR-code, offline invullen en
  afronden, versturen zodra er internet is en de pc aan staat.
- `pc.html`: speelt het programma op de pc na (Chrome of Edge). Toont de
  QR-code, ontvangt rapporten, geeft de klantenlijst mee.
- `gedeeld.js`: koppelcode en versleuteling, voor allebei.

Telefoon en pc praten via WebRTC met elkaar, zoals videobellen in de browser.
Een makelaartje (de gratis server van PeerJS) brengt ze in contact; lukt een
directe verbinding niet, dan gaat het via een doorgeefserver van PeerJS.
Alles is bovendien versleuteld met een sleutel uit de QR-code (AES-GCM), dus
geen van die servers kan iets lezen.

Er staan hier geen geheimen of gegevens in: de sleutel maakt de pc-pagina
zelf, in de browser, en hij staat alleen in de QR-code.
