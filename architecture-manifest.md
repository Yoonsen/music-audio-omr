# Hierarchical Bayesian Sensor Fusion for Music Recognition

## 1. Introduksjon: Et dynamisk felles-domene ($D$)

Tradisjonell Optical Music Recognition (OMR) og Automatic Music Transcription (AMT) behandles ofte som to isolerte problemer. Målet med dette prosjektet er å se på dem som et **Sensor Fusion**-problem, der verken bildet eller lyden er den absolutte sannheten, men heller støyfulle observasjoner av en underliggende, idealisert musikalsk virkelighet – heretter kalt domenet **$D$**.

Informasjonen flyter ikke bare én vei (fra bilde til symbol, eller lyd til symbol), men sirkulært. Bilde og lyd oppdaterer $D$, og $D$ legger føringer for hva bilde- og lydgjenkjenningen skal se etter.

## 2. Bruddet med tradisjonell OMR-litteratur

I klassisk OMR-litteratur er den dominerende arkitekturen ofte en asymmetrisk "feed-forward" pipeline (f.eks. tidlige systemer beskrevet av *Bainbridge & Bell, 2001*). En typisk flyt er:
1. Bildebehandling (binarisering, fjerning av notelinjer).
2. Symbol-klassifisering (Connected Components).
3. Sekvens-rekonstruksjon (Regelsystemer for å bygge XML/MEI).

Nyere systemer (*Calvo-Zaragoza et al., 2020*) bruker "End-to-End" maskinlæring, ofte via sekvens-til-sekvens modeller (CRNNs / Transformers) som oversetter et helt notebilde direkte til en symbolstreng (f.eks. verktøyet *Otsu* eller lignende end-to-end forskning).

Felles for nesten all OMR-litteratur er at de antar at **bildet alene definerer sannheten**, og strukturen er bygd utelukkende for å trekke mening *ut* av bildet. De mangler strukturer for *dynamisk oppdatering* (belief updating) av en latent modell basert på parallelle modaliteter. Ved å introdusere $D$ som et probabilistisk posisjonsrom, gjør vi systemet i stand til å ha en toveis informasjonsflyt. Auditiv evidens kan senke terskelen for å gjenkjenne en uskarpt trykket tone visuelt, og visuell geometri kan styre hvor i FFT-spekteret man leter etter lyden.

## 3. Arkitekturen: Fra Metadata til Piksler

Arkitekturen består av tre hovedlag, strukturert inspirert av Hierarkiske Bayesianske Modeller.

### Nivå 1: Globale Priors (Kontekst og Materiell Produksjon)
Dette er det ytterste laget som setter de statistiske forventningene (Bayesian Priors) *før* man begynner å analysere detaljdata.
* **Metadata:** Tittel, komponist, toneart (f.eks. "a-moll"). En a-moll prior øker start-sannsynligheten betraktelig for diatoniske toner over kromatiske.
* **Ensemble/Orkestrering:** "Trio", "Orkester", "Piano Solo". Dette definerer den fysiske forventningen til mediet (hvor mange notelinjer/staves arket bør ha, og hvor mange klangklasser lyden er delt inn i).

### Nivå 2: Den felles sannheten ($D$)
$D$ er en idealisert, auditivt-lenende representasjon av fremføringen. For å være kompatibel med "Type-Lowering" (bitmaps og boolsk algebra over posisjoner), defineres $D$ primært som et multidimensjonalt grid over fysisk tid ($t$) og pitch/frekvens ($p$).

$D$ populeres av trekkene (features):
* **$D_{onset}(t, p)$:** Sannsynlighet for at en tone initieres (anslag).
* **$D_{sustain}(t, p)$:** Sannsynlighet for at en tone fortsetter å klinge.
* **$D_{energy}(t, p)$:** Dynamikk og intensitet.
* **$D_{timbre}(t, p, c)$:** Sannsynlighet for at energien tilhører klang/instrument-klasse $c$.
* **$D_{metric}(t, m)$:** Mappingen som knytter fysisk tid $t$ til et musikalsk/metrisk anker $m$ (eks: takt 4, slag 1).

### Nivå 3: Projeksjoner (Observasjonsmodellene)
Dette er de reversible reglene (mappingene) som oversetter mellom det latente domenet $D$ og de rå sensordataene.
* **Visuelle projeksjoner ($D \leftrightarrow U_{image}$):** 
  * $D_{onset}$ forventer å finne geometriske notehoder (blobs) på de $(X,Y)$-koordinatene som tilsvarer gjeldende pitch og tidspunkt.
  * $D_{sustain}$ leter etter stiler, faner, bjelker og bindebuer.
  * $D_{metric}$ forventer vertikale taktstreker som strammer opp horisontal layout.
* **Auditive projeksjoner ($D \leftrightarrow U_{audio}$):**
  * $D_{onset}$ korrelerer med spektrale transienter og bredbåndsenergi i spesifikke frekvensbånd.
  * $D_{sustain}$ korrelerer med stabil harmonisk overtonestruktur.

## 4. Konklusjon: Sensor Fusion i Praksis
Fordi arkitekturen bygger på tensor/bitmap-grids (Type-Lowering), kan inferensen (dynamisk oppdatering) utføres via matrise- eller bit-operasjoner. Dersom lyden gjør en sterk observasjon, oppdateres distribusjonen i $D$. Dette gir $D$ mulighet til å sende sterkt vektede *priors* (tips) videre ned til bildegjenkjenningen, som da kan senke grenseverdiene (thresholds) sine for akkurat den delen av arket. Dermed avhjelper modalitetene hverandres usikkerhet på et svært lavt nivå i prosesseringskjeden.
