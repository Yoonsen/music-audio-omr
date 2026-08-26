# Handoff: lydassistert OMR for digitalisering av noter

## Bakgrunn og mål

Musikkseksjonen skal konvertere store mengder digitaliserte noteark med OMR.
Hovedoppgaven er fortsatt OMR: å lese den visuelle notasjonen og produsere et
strukturert, kontrollerbart partitur. Lyd skal undersøkes som en sekundær
informasjonskilde som kan løse lokale tvetydigheter der OMR-motoren er usikker.

Et viktig eksempel er en note under notesystemet: svak skanning, utydelige
hjelpelinjer eller dårlig estimert systemgeometri kan gjøre det uklart hvor
langt under systemet notehodet ligger. OMR kan da produsere flere plausible
tonehøyder. Dersom det finnes en tilhørende innspilling, kan den auditive
analysen bidra til å rangere kandidatene.

## Grunnidé

Modellen bør ha to innganger:

1. bilde av notearket, behandlet av OMR
2. lyd, representert som spektrogram og/eller estimerte tonehendelser

De møtes i en felles hendelses- og aligneringsmodell. Notearket gir den
diskrete strukturen: tonehøyde, notert varighet, takt, stemme, pauser og
symboler. Lyden gir den realiserte framføringen: faktisk tonehøyde og timing,
anslag, dynamikk, glissando, vibrato og artikulasjon.

Lydsiden bør i første omgang ikke skrive om partituret direkte. Den bør brukes
til å **rerangere OMR-motorens kandidater**. Dermed beholdes bildet som
primærkilde, mens lyd fungerer som evidens når bildet er tvetydig.

## Foreslått representasjon

Bruk `**kern` som partiturets semantiske representasjon, ikke som hele den
multimodale kjernen. `**kern` passer godt til noterte hendelser: tonehøyde,
varighet, stemmer, pauser, taktstreker, bindinger, buer, ornamenter og
artikulasjon.

Lag et tynt, separat skjema for framføringshendelser og koblingen mellom dem:

```text
ScoreEvent
  id
  kern_token
  part / staff / voice
  score_onset
  score_duration
  pitch_candidates[]
  omr_confidence
  page_bbox

AudioEvent
  id
  onset_seconds
  offset_seconds
  pitch / f0_curve
  attack
  intensity
  audio_confidence

Alignment
  score_event_ids[]
  audio_event_ids[]
  relation
  confidence
```

Koblingen må tillate mange-til-mange-relasjoner. Én notert tone kan realiseres
som trill eller glissando; flere noter kan bindes sammen; akkordtoner kan ha
ulike anslag; og en framføring kan utelate eller legge til toner.

## Mulig behandlingskjede

1. Finn systemer, notelinjer, takter, stemmer og symboler i bildet.
2. La OMR produsere én eller flere kandidater med sannsynlighet, ikke bare ett
   endelig svar.
3. Konverter de noterte kandidatene til `ScoreEvent` og etter hvert `**kern`.
4. Trekk ut tone-, onset- og uttrykksinformasjon fra lyden.
5. Lag først en grov tidsalignering mellom partitur og innspilling, deretter
   lokal hendelsesalignering.
6. Kombiner evidensen og reranger usikre OMR-kandidater.
7. Skriv valgt lesning til `**kern`, men behold alternativer, confidence og
   proveniens i en sidecar eller database for kontroll.

En forenklet beslutning kan uttrykkes slik:

```text
s_hat = argmax_s (log P(s | bilde) + lambda log P(lyd | s))
```

Her er `s` en lokal OMR-hypotese. Vekten `lambda` bør avhenge av lydkvalitet,
aligneringssikkerhet, instrumenttype og graden av polyfoni.

## Første avgrensede eksperiment

Start med tilfeller der OMR er usikker på vertikal noteposisjon og tonehøyde,
særlig:

- noter på og under hjelpelinjer
- svake eller brutte notelinjer
- notehoder som berører andre symboler
- fortegn med uklar tilknytning

Lag et lite fasitsett med bilde, eventuell lyd, korrekt tonehøyde og
OMR-motorens kandidatfordeling. Sammenlign:

1. OMR alene
2. lydtranskripsjon alene
3. OMR-kandidater rerangert med lyd

Mål både total nøyaktighet og nøyaktighet på tilfellene der OMR faktisk
uttrykker usikkerhet. Det viktigste første spørsmålet er ikke om lyd kan
transkribere stykket alene, men om den kan velge riktig blant noen få plausible
OMR-hypoteser.

## Forbehold

- Innspilling og partitur kan ha ulik toneart, stemming, repetisjoner, kutt
  eller ornamentering.
- Polyfon lyd gjør lokal toneidentifikasjon vanskelig; partiturkandidatene kan
  her redusere søkeområdet.
- Lyd skal ikke overstyre tydelig visuell evidens uten at avviket flagges.
- Systemet må fortsatt fungere som vanlig OMR når ingen passende innspilling
  finnes.
- Confidence og proveniens bør bevares slik at musikkfaglige kontrollører kan
  se hvorfor en lesning ble valgt.

## Oppgave ved åpning av repoet

Undersøk først:

- hvilke OMR-motorer og mellomformater repoet allerede bruker
- om motoren kan returnere N-best-kandidater, logits eller symbol-confidence
- hvor `**kern`, MusicXML eller MEI introduseres i kjeden
- om symbolene har stabile ID-er og koordinater tilbake til sidebildet
- hvilke evalueringsdata som finnes, spesielt vanskelige noter utenfor systemet
- om det finnes lydopptak som faktisk kan kobles til de aktuelle notene

Foreslå deretter den minste prototypen som kan teste lydassistert rerangering
uten å bygge om hele OMR-kjeden.
