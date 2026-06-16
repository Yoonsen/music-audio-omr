# Bayesian Sensor Fusion for Music Alignment: OMR & Audio via Positional Indexes

## 1. Konseptuell Arkitektur
Dette dokumentet beskriver en arkitektur for å synkronisere Optical Music Recognition (OMR) med Automatic Music Transcription (AMT/lyd) uten å bruke sekvensiell, regelbasert inferens. I stedet bruker vi **Type-Lowering** og **Bayesian Expectation-Maximization (EM)** over posisjonelle bit-indekser.

Målet er å tvinge to usikre støykilder (visuell støy og akustisk støy) til konsistens (likevekt) gjennom algebraiske operasjoner.

### Nøkkelkonsepter:
* **Type-Lowering:** Et token (f.eks. en note) betraktes ikke som et element *i* en sekvens. I stedet "senkes" det til å være en indikatorfunksjon over hele posisjonsuniverset $\mathcal{U}$. Et konsept er lik dets distribusjon.
* **Roaring Bitmaps:** Hver identitet (f.eks. $K_{C4}$) lagres som komprimerte bit-vektorer over tids/rom-aksen.
* **Bit-Sliced Indexing:** Kontinuerlige verdier (som energien i et chromagram eller sannsynlighetsgrad fra OMR) "skjæres opp" i binære lag (slices) for å tillate ren algebraisk prosessering uten å forlate bit-domenet.
* **Store Comonad (Komonade):** Nærhetssøk. Å tillate slingringsmonn (*slop*) betyr å la hver posisjon $p$ observere sitt nabolag $[p-k, p+k]$. Komonaden smører kontekst utover i universet.
* **Konsistenskrav (EM-Løkke):** Lyd-bitmaps maskereres over bilde-bitmaps med bitvise $\wedge$ (AND) og $\vee$ (OR) operasjoner. Inkonsistente hypoteser dør ut. Konsistente hypoteser forsterkes. Monaden stabiliserer representasjonen når fikspunktet nås: $C(C(x)) = C(x)$.

---

## 2. Instruksjoner for AI-Agent (Cursor / Copilot)
Når du genererer kode for dette systemet, **SKAL** følgende prinsipper følges:
1. **Unngå FOR-løkker for søk:** All matching mellom lyd og bilde skal skje via vektoriserte bit-operasjoner eller relasjonelle databassespørringer (SQLite/DuckDB).
2. **Klassisk Datasyn først:** Bruk `OpenCV` (projeksjonsprofiler for linjer, morfologi for blobber) for å generere OMR-hypotesene, ikke Deep Learning. Geometri genererer konfidens.
3. **Behold Usikkerheten:** Ikke terskle OMR-data tidlig. Om en blob kan være en C4 eller en D4, generer `True` i begge sine respektive bit-vektorer.

---

## 3. Python Eksempelkode: Den Komonadiske EM-Løkken

Dette er en forenklet, minnebasert demonstrasjon av hvordan bitvise operasjoner tvinger bilde og lyd til konsistens. I produksjon vil `numpy`-vektorene byttes ut med SQLite/Roaring Bitmaps.

```python
import numpy as np

class PositionalUniverse:
    def __init__(self, size):
        self.size = size
        # Posisjonsuniverset U. Kan representere frames eller taktslag.
        self.universe = np.arange(size)

def store_comonad_shift(bitmap, k_slop):
    """
    Komonadisk utvidelse (Store Comonad). 
    Lar en posisjon observere sitt nabolag ved å "smøre" bitmappet 
    med et slingringsmonn (slop) på +/- k.
    """
    smeared = np.copy(bitmap)
    for shift in range(1, k_slop + 1):
        # Shift høyre (se fremtidig kontekst)
        smeared[:-shift] |= bitmap[shift:]
        # Shift venstre (se historisk kontekst)
        smeared[shift:] |= bitmap[:-shift]
    return smeared

def bayesian_consistency_loop(omr_hypotheses, audio_chroma_slices, iterations=3):
    """
    Tvinger visuelle hypoteser og auditive fasiter til likevekt via bitmasking.
    """
    # Kopi for å la bitmappet "flyte" og oppdateres
    posterior = np.copy(omr_hypotheses)
    
    for i in range(iterations):
        # E-Steg (Observasjon): Komonaden sprer det akustiske nabolaget
        # Lydanalysen kan ha litt temporal offset, vi tillater slop.
        audio_context = store_comonad_shift(audio_chroma_slices, k_slop=1)
        
        # M-Steg (Stabilisering / Monade): Konsistenskrav
        # En visuell hypotese er kun gyldig hvis det finnes akustisk evidens i nabolaget.
        posterior = posterior & audio_context
        
        print(f"Iterasjon {i+1} Fikspunkt: {posterior.astype(int)}")
        
    return posterior

if __name__ == "__main__":
    # --- 1. INITIALISERING ---
    UNIVERSE_SIZE = 15 # 15 tidssteg
    
    # Rå OMR-data (Høy entropi). Systemet tror det er en C4 her, men er usikker pga støy (pos 4, 5, 6)
    # Et støvkorn har også skapt en falsk hypotese på pos 12.
    K_OMR_C4 = np.array([0,0,0, 1,1,1, 0,0,0,0, 0,1,0,0,0], dtype=bool)
    
    # Rå Lyd-data (Chromagram C-energi over terskel)
    # Lyden detekterer et tydelig anslag på pos 5 og 6.
    # Ingenting på pos 12 (det var et host, ingen C-energi).
    K_Audio_C_Slice = np.array([0,0,0, 0,1,1, 0,0,0,0, 0,0,0,0,0], dtype=bool)

    print("Init OMR (Hypotese):  ", K_OMR_C4.astype(int))
    print("Init Lyd (Evidens):   ", K_Audio_C_Slice.astype(int))
    print("-" * 40)

    # --- 2. KJØR LØKKEN ---
    final_index = bayesian_consistency_loop(K_OMR_C4, K_Audio_C_Slice, iterations=2)
    
    # --- 3. REALISERING ---
    # R-funktoren: Hent ut de faktiske posisjonene der lyden validerte bildet
    realized_positions = np.where(final_index == True)[0]
    print("-" * 40)
    print(f"Endelig sikker posisjons-indeks for C4: {realized_positions}")