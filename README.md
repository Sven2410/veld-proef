# OneDrive-proef

Een proef voor een boekhoudprogramma op Windows met een veld-app op de
telefoon, zonder eigen server: de telefoon zet een afgerond rapport in de
OneDrive van de gebruiker, en het programma op de pc haalt het daar op.

- `index.html`: de telefoonkant. Offline invullen en afronden, versturen
  zodra er internet is. Logt in bij Microsoft (MSAL.js) en schrijft alleen in
  de eigen map van de app in OneDrive (`Files.ReadWrite.AppFolder`).
- `pc.py`: de pc-kant. `inloggen`, `ophalen`, `klanten`, `status`.

Wat de proef moet laten zien: of het inloggen op de telefoon na een dag nog
staat (Microsoft geeft een web-app 24 uur), en hoe dat voelt in Safari en als
beginschermapp op een iPhone. Het logboek onderin de pagina houdt dat bij.

Het client ID in beide bestanden is geen geheim; er staan hier geen tokens of
gegevens in.
