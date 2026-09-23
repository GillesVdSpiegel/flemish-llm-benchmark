# LinkedIn-post (NL)

> Versie 1 · klaar om te posten zodra de GitHub-repo publiek staat.

---

**Kent uw AI-model Vlaams? Ik heb het gemeten.**

Nederlandstalige AI-evaluatie maakt zelden onderscheid tussen Belgisch- en Nederlands-Nederlands.
Voor Vlaamse organisaties die deze tools inzetten, is dat net de vraag.

Het probleem bij zo'n vergelijking: als de Belgische vragen gewoon moeilijker zijn, bewijst een
lagere score niets. Daarom is elk Belgisch woord gekoppeld aan een Nederlands woord dat **even goed
gekend is in eigen land**, op basis van prevalentiecijfers van 54.000 woorden (Brysbaert et al.).
Gemiddeld verschil binnen een paar: 0,6 procentpunt.

493 woordparen, 986 vragen, 7 modellen, ongeveer € 1 aan API-kosten.

Het opvallendste resultaat gaat niet over de grote modellen:

• **ChocoLlama** (getraind op Belgische én Nederlandse data): **+9,7 punten béter** op
Belgisch-Nederlands
• **GEITje** (overwegend Nederlandse data): **−6,4 punten**
• Claude, GPT en Gemini: 1 tot 4 punten lager op Belgisch, maar die zitten met 97-100 % al tegen
het plafond

Kortom: wie Belgische data in de training stopt, wint daar zichtbaar mee. Bij de grootste modellen
is het verschil klein, maar het wijst wel telkens dezelfde kant op.

Wat het níét aantoont: dit gaat over losse woordbetekenis. Administratieve taal, tussentaal en
Belgische instellingenkennis zitten er niet in, en er is nog geen menselijke referentiescore. Die
beperkingen staan voluit in de methodetekst.

Dataset (CC BY 4.0): huggingface.co/datasets/Goomey/flembench
Code, methode en volledige resultaten: <GitHub-link>

#AI #NLP #Nederlands #Vlaanderen #TaalTechnologie
