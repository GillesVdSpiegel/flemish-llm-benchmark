# Kent uw AI-model Vlaams? Een gepaarde meting van woordenschat

**Versie 1 · 22 september 2026 · [github.com/GillesVdSpiegel/flemish-llm-benchmark](https://github.com/GillesVdSpiegel/flemish-llm-benchmark)**

## Kort samengevat

Taalmodellen kennen Belgisch-Nederlandse woorden even goed of iets minder goed dan
Nederlands-Nederlandse woorden van dezelfde moeilijkheidsgraad. Het verschil is klein voor de
grote commerciële modellen (2 tot 4 procentpunten) en volgt bij de kleinere, Nederlandstalige
modellen vooral hun trainingsdata:

| Model | Belgisch | Nederlands | Kloof | 95%-BI | p |
|---|---|---|---|---|---|
| **ChocoLlama-8B** (BE + NL data) | 69,2 % | 59,5 % | **+9,7** | +3,2 … +15,8 | 0,004 ✔ |
| **GEITje-7B-ultra** (NL-data) | 78,8 % | 85,3 % | **−6,4** | −11,8 … −1,3 | 0,022 |
| GPT-5.6 Terra | 92,5 % | 96,0 % | −3,5 | −7,0 … −0,3 | 0,060 |
| Claude Sonnet 5 | 96,8 % | 98,4 % | −1,6 | −3,8 … +0,5 | 0,210 |
| EuroLLM-9B | 88,2 % | 89,8 % | −1,6 | −6,2 … +2,9 | 0,561 |
| Gemma 4 12B | 63,3 % | 63,0 % | +0,3 | −6,7 … +7,0 | 1,000 |

Een positieve kloof betekent: beter op Belgisch-Nederlands. Cijfers voor de 373 "schone" paren
(zie [Methode](#methode)). Na correctie voor het testen van zes modellen (Holm) blijft alleen
ChocoLlama significant.

**De kern van het resultaat is niet "modellen kunnen geen Vlaams".** Het is: *wie Belgische data
in de training stopt, wint er ongeveer tien punten mee; wie dat niet doet, verliest er een
handvol.* Bij de grootste modellen is het verschil klein, maar het wijst wel consequent dezelfde
kant op.

## Onderzoeksvraag

Presteren huidige taalmodellen meetbaar slechter op Belgisch-Nederlands dan op
Nederlands-Nederlands? Deze eerste versie beantwoordt die vraag voor één duidelijk afgebakend
onderdeel: **woordbetekenis**.

Bestaande Nederlandstalige evaluaties (EuroEval, de Amsterdamse overheidsbenchmark, DUMB) maken
geen onderscheid tussen beide variëteiten. Voor zover bekend is dit de eerste gepaarde meting
BE/NL bij taalmodellen.

## Methode

### Woordparen met gelijke moeilijkheidsgraad

De kern van het ontwerp is dat elk Belgisch woord gekoppeld is aan een Nederlands woord dat
**even goed gekend is in eigen land**. Zonder die koppeling meet je vooral of de ene woordenlijst
toevallig moeilijker is dan de andere.

Daarvoor gebruiken we de prevalentienormen van het Dutch Crowdsourcing Project (Brysbaert,
Keuleers, Mandera & Stevens, 2019): voor 54.000 woorden is apart gemeten welk aandeel van de
Belgen en van de Nederlanders het woord kent.

1. **Kandidaten**: woorden die minstens 80 % van de eigen bevolking kent en minstens 30
   procentpunten minder in het andere land: 584 Belgische en 497 Nederlandse woorden.
2. **Koppeling**: één-op-één matching op eigen bekendheid (± 3 punten) en op het verschil tussen
   beide landen (± 5 punten). Resultaat: **493 paren**, met een gemiddeld verschil in eigen
   bekendheid van **0,6 procentpunt**.
3. **Vragen**: per woord één meerkeuzevraag met hetzelfde sjabloon voor beide variëteiten.

> Wat betekent het woord "zwalpen" zoals het in België gebruikt wordt?
> A. klotsen  B. treuzelen  C. een beetje dik  D. dorpsplein

De drie afleiders zijn betekenissen van andere woorden uit de lijst, zonder gedeelde inhoudswoorden
met het juiste antwoord en van vergelijkbare lengte. Het juiste antwoord staat bij beide leden van
een paar op dezelfde positie, zodat een voorkeur voor letter A of B geen kloof kan veroorzaken.

### Schone paren en vormgelijkenis

Bij 120 paren lijkt de betekenis op het woord zelf (*bakkerin* → *bakkersvrouw*). Een model kan die
dan raden op vorm. Die paren krijgen het label `A1a-overlap` en tellen niet mee voor het
hoofdcijfer; de overige **373 paren** (`A1a-clean`) dragen het resultaat. Beide worden gerapporteerd.

### Herkomst van de juiste antwoorden

De betekenissen zijn opgesteld door twee onafhankelijke modellen (Claude Opus 5 en Gemini) en
daarna nagekeken:

- **1.018 van 1.081** betekenissen: beide modellen kwamen onafhankelijk op dezelfde betekenis uit;
- **63** betekenissen waarover ze het oneens waren, zijn stuk voor stuk door de auteur beslist;
- **11 twijfelgevallen** aan Nederlandse kant zijn voorgelegd aan een Nederlandse moedertaalspreker,
  die 7 betekenissen gaf en 4 woorden afkeurde (verouderd of niet variëteitspecifiek).

Elk item registreert waar zijn juiste antwoord vandaan komt. Dat is nodig voor een eerlijke
beoordeling: de betekenissen zijn deels door modellen opgesteld, en Claude zit zelf in de test.
Zie [Beperkingen](#wat-dit-onderzoek-niet-aantoont).

### Modellen en runcondities

| Model | Toegang | Redeneren |
|---|---|---|
| Claude Sonnet 5 | Anthropic API | uitgeschakeld (temperatuur wordt niet ondersteund) |
| GPT-5.6 Terra | OpenAI API | effort `none` |
| Gemini 3.8 Flash | Gemini API | *niet afgerond: zie onder* |
| EuroLLM-9B-Instruct-2512 | lokaal, Q8_0 | geen, temperatuur 0, vaste seed |
| GEITje-7B-ultra | lokaal, Q8_0 | idem |
| Llama-3-ChocoLlama-8B-instruct | lokaal, Q8_0 | idem |
| Gemma 4 12B | lokaal, officiële QAT 4-bit | denken uit |

Alle modellen kregen exact dezelfde instructie in neutraal Standaardnederlands. De lokale modellen
zijn geprompt met hun **eigen originele chattemplate**, en een controle toont dat elk model precies
evenveel tokens ontvangt als met zijn oorspronkelijke tokenizer: een verkeerd sjabloon zou een
model stil benadelen.

Totale API-kost voor de volledige meting: **ongeveer € 1**.

## Resultaten

### De kloof per model

Zie de tabel bovenaan. Vier van de zes modellen scoren lager op Belgisch-Nederlands, één scoort
hoger (ChocoLlama) en één toont geen verschil (Gemma).

### Moeilijkere woorden zijn ook voor modellen moeilijker

Gemiddeld over de zes modellen, per bekendheidsklasse in eigen land:

| Gekend door … van eigen bevolking | Belgisch | Nederlands |
|---|---|---|
| 79–85 % | 75,9 % | 80,5 % |
| 85–90 % | 81,1 % | 84,7 % |
| 90–95 % | 82,6 % | 84,4 % |
| 95–100 % | 88,6 % | 89,0 % |

Dat de curve netjes stijgt, is een teken dat de test meet wat ze moet meten. In elke klasse ligt de
Belgische kant iets lager.

### Welke woorden gaan mis

Belgische woorden die de meeste modellen missen: *konijnenpijp*, *balkleed*, *bezetsel*,
*roefelen*, *baancafé*, *champetter*, *nieuwkuis*, *vidé*, *witteke*, *omwringen*.

Nederlandse woorden die de meeste modellen missen: *apezuur*, *glom*, *poepdoos*, *klunen*,
*moetje*, *eigenheimer*, *gierton*, *bul*.

Aan Belgische kant vallen eten, drank en huishouden op (*vidé*, *witteke*, *nieuwkuis*,
*bezetsel*). Precies bij die woorden gaven de modellen eerder ook zelf een foute betekenis op.

Eén item wordt door alle zes modellen fout beantwoord: *konijnenpijp* (konijnenhol), waar ze
allemaal "aanbouwsel, bijgebouwtje" kiezen.

### Hoe stabiel zijn de antwoorden?

Elk model kreeg een deelverzameling van 60 paren drie keer voorgelegd, met identieke instellingen.
Het aandeel vragen waarop alle drie de antwoorden gelijk zijn:

| Model | Identiek antwoord in 3 runs |
|---|---|
| GEITje-7B-ultra | 99,2 % |
| Claude Sonnet 5 | 99,1 % |
| EuroLLM-9B | 98,3 % |
| Gemma 4 12B | 98,3 % |
| GPT-5.6 Terra | 96,5 % |
| ChocoLlama-8B | 93,3 % |

Geen enkel model is volledig deterministisch, ook niet lokaal met temperatuur 0 en een vaste seed.
Praktisch betekent dit: **verschillen kleiner dan ongeveer 1 tot 2 procentpunten kunnen ruis zijn**,
voor ChocoLlama iets meer. Alle gerapporteerde kloven boven de 3 punten liggen daarboven.

### Geen aanwijzing voor systematische vertekening

Als een model fout antwoordt, kiest het ongeveer even vaak een Belgische als een Nederlandse
betekenis als afleider. Het aandeel onleesbare antwoorden is 0,0 % voor alle modellen behalve
Gemma (0,3 %).

## Wat dit onderzoek niet aantoont

- **Geen uitspraak over "Vlaams" in het algemeen.** Gemeten is losse woordbetekenis, zonder context
  en zonder zinsbouw. Administratieve taal, tussentaal in gesprekken, uitspraak en Belgische
  instellingenkennis zitten niet in deze versie.
- **Plafondeffect bij de sterkste modellen.** Claude zit op 97–98 %. Er is weinig ruimte over om
  een verschil te meten; de kleine kloof van 1,6 punt is daardoor niet goed te onderscheiden van nul.
- **De juiste antwoorden zijn deels door modellen opgesteld.** Twee modellen van verschillende
  makers moesten het eens zijn, en de twijfelgevallen zijn met de hand beslist, maar Claude heeft de
  meeste betekenissen geschreven en zit ook in de test. Een voordeel voor Claude valt niet uit te
  sluiten.
- **Statistische scherpte.** Met 373 paren is het betrouwbaarheidsinterval ongeveer ± 4 punten bij
  sterke modellen en tot ± 7 bij zwakke. Verschillen kleiner dan dat blijven onzichtbaar.
- **Zes modellen, zes toetsen.** Na Holm-correctie houdt alleen ChocoLlama stand. De richting van de
  overige resultaten is suggestief, geen bewijs.
- **Gemini ontbreekt.** Op 22 september 2026 waren Gemini 3.8 en 3.7 Flash urenlang onbeschikbaar
  ("high demand"); 2 van 986 vragen raakten beantwoord. Dat zegt niets over de taalkwaliteit van het
  model, wel iets over beschikbaarheid.
- **Lokale modellen draaien gekwantiseerd** (Q8_0, Gemma 4-bit). Kwantisatie kan prestaties drukken,
  vermoedelijk voor beide variëteiten gelijk.
- **Geen menselijke referentie.** De modelscores zijn niet vergeleken met mensen die dezelfde
  vragen beantwoorden. Daardoor weten we wel hoe modellen zich onderling verhouden, maar niet hoe
  ze zich verhouden tot een Vlaamse of Nederlandse moedertaalspreker. De koppeling op
  prevalentie maakt beide kanten even moeilijk *voor mensen in eigen land*, maar dat is een
  indirecte maatstaf; een directe meting ontbreekt. Dit is het grootste hiaat van v1.
- **Eén auteur.** Een tweede Vlaamse beoordelaar heeft nog geen steekproef nagekeken; die controle
  volgt in een volgende versie.

## Reproduceren

```bash
uv sync --all-extras
uv run flembench generate-a1                 # bouwt de vragen uit de woordparen
uv run flembench estimate claude-sonnet-5    # kost vooraf
uv run flembench run claude-sonnet-5 --budget 1
uv run flembench rescore                     # scoort alles opnieuw uit de cache
uv run python scripts/error_analysis.py
```

Alle antwoorden van de modellen zitten in `runs/cache/`, zodat opnieuw scoren nooit opnieuw hoeft
te betalen. 20 % van de paren zit in een private held-out set, zodat later te controleren valt of de
publieke set in trainingsdata terechtkomt.

## Bronnen en licenties

- Prevalentienormen: Brysbaert, Keuleers, Mandera & Stevens (2019), *Recognition Times for 54
  Thousand Dutch Words*, Psychologica Belgica 59(1), data via [osf.io/5fk8d](https://osf.io/5fk8d/)
  (CC BY-NC 4.0). De normwaarden zelf worden niet meegepubliceerd, alleen de woordkeuze die eruit
  volgt.
- Code: MIT. Dataset: CC BY 4.0.
- Modellen: zie `config/models.yaml` en `config/local_models.yaml` (gewichten vastgelegd op SHA-256).
