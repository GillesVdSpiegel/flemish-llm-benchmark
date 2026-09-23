# flembench — kent uw AI-model Vlaams?

**🇧🇪 Nederlands** · [🇬🇧 English](README.en.md)

**Presteren taalmodellen meetbaar slechter op Belgisch-Nederlands dan op Nederlands-Nederlands?**
493 gekoppelde woordparen, 986 vragen, 7 modellen, ongeveer € 1,15 aan API-kosten.

![De Vlaamse kloof per model](analysis/kloof.png)

| Model | Belgisch | Nederlands | Kloof | 95%-BI | p |
|---|---|---|---|---|---|
| **ChocoLlama-8B** (Belgische + NL trainingsdata) | 69,2 % | 59,5 % | **+9,7** | +3,2 … +15,8 | 0,004 ✔ |
| **GEITje-7B-ultra** (overwegend NL-data) | 78,8 % | 85,3 % | **−6,4** | −11,8 … −1,3 | 0,022 |
| GPT-5.6 Terra | 92,5 % | 96,0 % | −3,5 | −7,0 … −0,3 | 0,060 |
| Claude Sonnet 5 | 96,8 % | 98,4 % | −1,6 | −3,8 … +0,5 | 0,210 |
| EuroLLM-9B | 88,2 % | 89,8 % | −1,6 | −6,2 … +2,9 | 0,561 |
| Gemini 3.8 Flash | 98,7 % | 100,0 % | −1,3 | −2,7 … −0,3 | 0,062 |
| Gemma 4 12B | 63,3 % | 63,0 % | +0,3 | −6,7 … +7,0 | 1,000 |

Een positieve kloof betekent *beter* op Belgisch-Nederlands. Na Holm-correctie voor zeven modellen
blijft enkel de kloof van ChocoLlama op zichzelf significant.

## Kort samengevat

Nederlandstalige AI-evaluatie maakt zelden onderscheid tussen Belgisch- en Nederlands-Nederlands.
Voor Vlaamse organisaties die deze tools inzetten, is dat net de vraag.

Het probleem bij zo'n vergelijking: als de Belgische vragen gewoon moeilijker zijn, bewijst een
lagere score niets. Daarom is elk Belgisch woord gekoppeld aan een Nederlands woord dat **even goed
gekend is in eigen land**, op basis van prevalentiecijfers van 54.000 woorden. Gemiddeld verschil
binnen een paar: **0,6 procentpunt**.

Het opvallendste resultaat gaat niet over de grote modellen:

- **ChocoLlama** (het enige model met Belgische trainingsdata) scoort **9,7 punten beter** op
  Belgisch-Nederlands.
- **GEITje** (vooral Nederlandse data) scoort **6,4 punten slechter** — zelfde grootteorde,
  omgekeerde richting.
- **Claude, GPT en Gemini** liggen 1 tot 4 punten lager op Belgisch, maar zitten met 97-100 % al
  tegen het plafond; hun cijfers zijn dus ondergrenzen.

Kortom: wie Belgische data in de training stopt, wint daar zichtbaar mee. Bij de grootste modellen
is het verschil klein, maar het wijst bij vijf van de zeven modellen dezelfde kant op.

Volledige methodetekst: **[docs/bevindingen.md](docs/bevindingen.md)** ·
Dataset: **[huggingface.co/datasets/Goomey/flembench](https://huggingface.co/datasets/Goomey/flembench)**

---

## Hoe het werkt, technisch

### 1. De koppeling ís het ontwerp

Woordkennis wordt gemeten, niet verondersteld. Het Dutch Crowdsourcing Project (Brysbaert,
Keuleers, Mandera & Stevens 2019) registreerde voor 54.000 woorden welk aandeel van de **Belgen** en
welk aandeel van de **Nederlanders** elk woord kent.

- **Kandidaten:** gekend door ≥ 80 % in eigen land en ≥ 30 punten minder in het andere land → 584
  Belgische en 497 Nederlandse woorden.
- **Koppeling:** één-op-één toewijzing (Hongaars algoritme) op eigen bekendheid (± 3 punten) en op
  het verschil tussen beide landen (± 5 punten) → **493 paren**, gemiddeld verschil binnen een paar
  0,6 punt.
- Omdat de menselijke moeilijkheidsgraad per constructie gelijk is, is een verschil in modelscores
  een eigenschap van het model en niet van de woordenlijst.

Volledige afweging, verworpen alternatieven en nadelen:
**[docs/decisions/0001-pairing.md](docs/decisions/0001-pairing.md)**.

### 2. Vragen worden gegenereerd, niet met de hand geschreven

Eén sjabloon voor beide variëteiten, zodat niets verschilt behalve het woord en de landnaam:

> Wat betekent het woord "zwalpen" zoals het in België gebruikt wordt?
> A. klotsen · B. treuzelen · C. een beetje dik · D. dorpsplein

- **Afleiders** zijn betekenissen van andere woorden uit de verzameling, gefilterd op: geen gedeeld
  inhoudswoord met het juiste antwoord, geen gelijkenis met het doelwoord, vergelijkbare lengte.
- **Het juiste antwoord staat bij beide leden van een paar op dezelfde positie**, zodat een voorkeur
  voor een bepaalde letter (ChocoLlama kiest in 49 % van de gevallen "A") geen kloof kan veroorzaken.
- **120 paren waarvan de betekenis op het woord zelf lijkt** (*bakkerin* → *bakkersvrouw*) krijgen
  het label `A1a-overlap` en tellen niet mee voor het hoofdcijfer; ze worden apart gerapporteerd.

### 3. De juiste antwoorden hebben een traceerbare herkomst

De betekenissen zijn onafhankelijk opgesteld door twee modellen van verschillende makers en daarna
nagekeken:

| Bron | Aantal |
|---|---|
| Claude en Gemini kwamen onafhankelijk tot dezelfde betekenis | 1.018 van 1.081 |
| Onenigheid, beslist door de auteur (Vlaamse moedertaalspreker) | 63 |
| Twijfelgevallen beslist door een Nederlandse moedertaalspreker | 11 (4 afgekeurd) |

Elk item registreert `drafted_by` en `reviewed_by`, zodat iedereen kan nagaan of de door modellen
opgestelde antwoorden het resultaat hebben gekleurd. Dat is nodig, want een van de opstellers
(Claude) zit zelf in de test.

### 4. Statistiek

- **Gepaarde vergelijking:** de kloof is het gemiddelde over paren van (Belgisch juist − Nederlands
  juist).
- **95 %-betrouwbaarheidsintervallen** via bootstrap **over paren** (10.000 herbemonsteringen), niet
  over items.
- **Exacte McNemar-toets** per model, **Holm-gecorrigeerd** over de zeven modellen.
- **Variantie:** 60 paren, drie keer per model. 93-99 % identieke antwoorden; geen enkel model is
  volledig deterministisch, ook niet lokaal bij temperatuur 0 met vaste seed. Verschillen onder 1 à
  2 punten zijn ruis.
- **Held-out set:** 20 % van de paren staat in een private repo, zodat later te controleren valt of
  de publieke set in trainingsdata belandt.

### 5. Engineering

- **Eén adapterinterface** voor Anthropic, OpenAI, Gemini en lokale modellen via Ollama; de
  runcondities (redeneren uit of minimaal) staan per model geregistreerd, want ze zijn niet
  uniform.
- **Elk antwoord wordt gecached**, zodat herscoren gratis en reproduceerbaar is: `flembench rescore`
  bouwt alle resultaten opnieuw op zonder één API-oproep.
- **Kostenraming vóór elke run** plus een harde budgetlimiet.
- **Lokale modelgewichten vastgelegd op SHA-256**; `scripts/check_local_tokenization.py` controleert
  dat elk lokaal model exact de tokenreeks krijgt die zijn oorspronkelijke tokenizer zou
  produceren, want een verkeerd chatsjabloon benadeelt een model stilzwijgend.
- **83 tests, zonder netwerk**; CI draait lint, tests, schemavalidatie van de items en een
  schemadriftcontrole.

## Reproduceren

```bash
uv sync --all-extras
cp .env.example .env            # API-sleutels invullen
uv run flembench generate-a1    # bouwt de vragen uit de woordparen
uv run flembench estimate claude-sonnet-5
uv run flembench run claude-sonnet-5 --budget 1
uv run flembench rescore        # herscoort alles uit de cache, zonder API-oproepen
uv run python scripts/error_analysis.py
```

## Wat dit onderzoek niet aantoont

- **Enkel losse woordbetekenis** — geen context, geen zinsbouw, geen administratieve taal, geen
  instellingenkennis.
- **Plafondeffect** bij de sterkste modellen, waardoor hun kloof een ondergrens is.
- **Juiste antwoorden deels door modellen opgesteld**, en een van die modellen zit in de test.
- **Geen menselijke referentie:** modelscores zijn niet vergeleken met moedertaalsprekers op
  dezelfde vragen.
- **Zeven modellen, zeven toetsen:** na correctie blijft één verschil op zichzelf staan.
- **Lokale modellen draaien gekwantiseerd** (Q8_0, Gemma 4-bit).

De volledige lijst met redenering staat in de
[methodetekst](docs/bevindingen.md#wat-dit-onderzoek-niet-aantoont).

## Wegwijs in de repo

| Pad | Inhoud |
|---|---|
| `src/flembench/` | harnas: adapters, cache, scoring, statistiek, itemgeneratie |
| `items/A1/auto/` | de 394 publieke vraagparen (YAML, één bestand per paar) |
| `data/` | gecompileerde dataset, curatiebeslissingen, dataset card |
| `runs/cache/` | elk modelantwoord, voor reproduceerbaar herscoren |
| `analysis/` | foutenanalyse en de hoofdfiguur |
| `docs/` | methodetekst, ontwerpdocument, beslissingsdocumenten |

## Licenties

Code MIT (`LICENSE`), dataset CC BY 4.0 (`LICENSE-DATA.md`). De woordselectie is afgeleid van normen
onder CC BY-NC 4.0, die hier niet mee gepubliceerd worden.
