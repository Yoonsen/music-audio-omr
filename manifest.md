# Positional Indexes for Music Recognition

## 1. Background

This project starts from the type-lowering idea developed in
`type-lowering.pdf`.

The point is not to imagine that the CPU has been lifted into some more
powerful abstract machine. The CPU already has word-level and SIMD-style
parallelism. The useful move is to lower the data into a representation where
that existing parallelism becomes directly available.

In the type-lowered representation, an object is no longer treated primarily as
an item inside a sequence. It becomes an indicator field over a position
universe:

```text
token A in a sequence
    becomes
bitmap A over positions U
```

The sequence has not disappeared. Its order has moved from control flow into
data layout. Operations such as intersection, union, shifting, neighborhood
expansion, and counting can then be expressed as algebra over whole positional
fields.

## 2. Music as Sensor Fusion

The music-recognition idea is to use the same positional view for two uncertain
sources of evidence:

```text
notated page  -> visual evidence
performance   -> acoustic evidence
```

Neither source is a final truth. The page can be noisy, ambiguous, distorted, or
partly unreadable. The audio can contain expressive timing, room noise,
overtones, missing attacks, or pitch material that is not cleanly separable.

The goal is therefore not to make OMR and audio match point by point. The goal
is to let them annotate and constrain each other.

```text
OMR hypotheses can explain parts of the audio.
Audio evidence can validate or weaken parts of the OMR.
```

This is closer to alignment between speech and writing than to exact equality.
Speech contains prosody, timing, breath, and noise that are not present in
writing. Writing contains spaces, punctuation, and normalized forms that are not
directly present in speech. They meet at stable anchors. Music has a similar
shape.

## 3. Distinct but Alignable Universes

The first conservative assumption is that the relevant domains may not share
one common index space.

```text
U_image   pixel and staff geometry
U_score   symbolic or quasi-symbolic score positions
U_audio   time frames, onsets, and spectral evidence
U_anchor  musically meaningful landmarks
```

The image domain may be much finer than the symbolic score domain. The audio
domain may be finer in time but coarser in symbolic structure. A staff line, a
notehead, a chroma peak, a barline, and a performed onset need not occupy the
same kind of position.

The useful structure is therefore not necessarily equality of positions, but
alignment through projections and relations:

```text
L_image : Image -> Evidence(U_image)
L_omr   : Evidence(U_image) -> Evidence(U_score)
L_audio : Audio -> Evidence(U_audio)
A       : U_score <-> U_audio
P       : Evidence(U_score or U_audio) -> Evidence(U_anchor)
```

The project should remain open to the possibility that a single shared universe
is too rigid. A more realistic model may use coupled universes that meet only at
important musical anchors.

## 4. Annotation Instead of Equality

The next concept, not yet developed in the type-lowering note, is annotation.

An annotation is an asymmetric relation between positional fields. One field
does not have to equal another. It may cover it, be covered by it, touch it at
anchors, or provide partial support for it.

Examples:

```text
notehead position     annotates likely pitch
stem or beam          annotates duration class
barline               annotates metric boundary
audio onset           annotates attack position
chroma energy         annotates pitch-class region
tempo curve           annotates score-time mapping
```

This suggests a small algebra of bitmap relations:

```text
overlap(a, b)   = popcount(a & b)
coverage(a, b)  = popcount(a & b) / popcount(b)
precision(a, b) = popcount(a & b) / popcount(a)
contains(a, b)  = (a & b) == b
```

The exact thresholds and meanings depend on the annotation type. An onset may
only under-cover a notated duration. A slur may over-cover several notes. A
barline may be a thin visual object but a strong anchor in score space.

Consistency therefore means:

```text
Different lowered fields agree enough on the relations that matter.
```

It does not mean that they are identical.

## 5. Store Comonad as Local Observation

The Store-comonad intuition from `type-lowering.pdf` remains useful: proximity
is observation from a focused position into its neighborhood.

For music recognition, this is a way to talk about tolerance:

```text
Does this audio onset occur near a predicted score event?
Does this notehead lie near a staff position?
Does this visual cluster sit near a plausible rhythmic anchor?
```

The neighborhood can live in different universes:

```text
near_image  : local pixel/staff neighborhood
near_score  : nearby symbolic positions
near_audio  : nearby frames or onsets
near_anchor : nearby musical landmarks
```

This keeps slop or tolerance from becoming an ad hoc exception. It is a local
observation rule over a chosen positional universe.

## 6. Research Strategy

This repository should grow slowly.

The first goal is not a full OMR or transcription system. The first goal is to
learn which lowered evidence fields can be extracted simply and reliably.

Initial experiments should be small notebooks:

```text
01_omr_probe       staff lines, projection profiles, simple morphology
02_audio_probe     waveform, FFT, spectrogram, chroma or onset evidence
03_index_probe     synthetic bitmaps, annotation relations, coverage metrics
```

Each notebook should answer one practical question:

```text
What evidence field can we extract?
How noisy is it?
What positional universe does it naturally live in?
What would it be able to annotate?
```

This makes the work collaborative and inspectable. The human should be able to
look at each intermediate image, plot, or bitmap and decide whether the next
step is justified.

## 7. Current First Step

Start with the notated page.

The first notebook should not try to recognize notes. It should ask a smaller
question:

```text
Can simple image processing find staff-line evidence?
```

If staff lines can be located robustly, they become an early bridge from
`U_image` to `U_score`. If they cannot, the project learns that the visual
front-end needs more care before audio fusion is meaningful.

