def bayesian_enharmonic_spelling(midi_note, context_priors):
    """
    Beregner den mest sannsynlige enharmoniske stavingen for en gitt MIDI-note
    ved bruk av Bayes' teorem.
    """
    
    # 1. Definer hypotesene (x) for MIDI 66
    hypotheses = ["F#", "Gb"]

    # 2. Likelihood: P(D | x)
    # Gitt at stavingen er F# eller Gb, hvor sannsynlig er det at vi hører MIDI 66?
    # I likestemming er denne 1.0 for begge (de er akustisk identiske).
    likelihoods = {
        "F#": 1.0, 
        "Gb": 1.0
    }

    # 3. Beregn Total Evidens / Marginal Likelihood: P(D)
    # P(D) = Σ [ P(D | x) * P(x) ] for alle hypoteser
    p_d = sum(likelihoods[note] * context_priors[note] for note in hypotheses)

    # 4. Beregn Posterior: P(x | D)
    # P(x | D) = (P(D | x) * P(x)) / P(D)
    posteriors = {}
    for note in hypotheses:
        posteriors[note] = (likelihoods[note] * context_priors[note]) / p_d

    # 5. Finn stavingen med høyest sannsynlighet
    best_spelling = max(posteriors, key=posteriors.get)

    return best_spelling, posteriors

# --- Kjøring av eksempler ---

print("=== Scenario 1: Kontekst er D-dur ===")
# I D-dur er F# terts, mens Gb er et kromatisk avvik.
priors_d_major = {
    "F#": 0.95,
    "Gb": 0.05
}

best_1, post_1 = bayesian_enharmonic_spelling(66, priors_d_major)
print(f"Priors: {priors_d_major}")
print(f"Posterior Sannsynligheter: {post_1}")
print(f"Valgt staving i kern: {best_1}\n")

print("=== Scenario 2: Kontekst er Db-dur ===")
# I Db-dur er Gb ren kvart, mens F# er et kromatisk avvik.
priors_db_major = {
    "F#": 0.05,
    "Gb": 0.95
}

best_2, post_2 = bayesian_enharmonic_spelling(66, priors_db_major)
print(f"Priors: {priors_db_major}")
print(f"Posterior Sannsynligheter: {post_2}")
print(f"Valgt staving i kern: {best_2}")