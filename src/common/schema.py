"""Shared categories for every track. Change only via PR, with a heads-up to all tracks."""

AGE_BANDS = ("18-24", "25-34", "35-44", "45-54", "55-64", "65+")
AGE_EDGES = (18, 25, 35, 45, 55, 65)  # lower bound (years) of each AGE_BANDS entry
GENDERS = ("male", "female")
EDUCATION_LEVELS = ("primary", "secondary", "vocational", "bachelor", "graduate")
SETTLEMENT_TYPES = ("urban", "rural")
MARITAL_STATUSES = ("married", "single", "divorced", "widowed")
EMPLOYMENT_STATUSES = ("employed", "unemployed", "student", "retired", "homemaker")
INCOME_DECILES = tuple(range(1, 11))
# The 7 geographic regions; the 12 NUTS-1 regions collapse onto these (personas/wvs.py).
REGIONS = ("Marmara", "Ege", "Akdeniz", "Ic Anadolu", "Karadeniz", "Dogu Anadolu", "Guneydogu Anadolu")

CONDITIONING_FIELDS = (
    "persona_id",
    "age_band",
    "gender",
    "education_level",
    "region",
    "settlement_type",
    "marital_status",
    "employment_status",
    "income_decile",
)

# Allowed values per categorical conditioning field.
CATEGORIES = {
    "age_band": AGE_BANDS,
    "gender": GENDERS,
    "education_level": EDUCATION_LEVELS,
    "region": REGIONS,
    "settlement_type": SETTLEMENT_TYPES,
    "marital_status": MARITAL_STATUSES,
    "employment_status": EMPLOYMENT_STATUSES,
    "income_decile": INCOME_DECILES,
}

# personas.csv columns, in contract order.
PERSONA_COLUMNS = ("persona_id", "cell_id", "weight", *CONDITIONING_FIELDS[1:])

# The fields that define an archetype cell (cell_id = "age_band|gender|education_level").
CELL_FIELDS = ("age_band", "gender", "education_level")

# Never visible to persona generation or simulation; validation only (Track C).
# Track C (Hasan) sign-off: two items per topic -- one to FIT (calibrate) and
# one to TEST (measure accuracy) -- so accuracy is measured on items that never
# touched calibration. Source WVS-7 item and scale noted per field; trust and
# religious_identity stay categorical, the rest keep their raw survey scale.
HELDOUT_FIELDS = (
    "trust_government",        # Q71  confidence, categorical  (fit)
    "trust_courts",           # Q70  confidence, categorical  (fit)
    "trust_police",           # Q69  confidence, categorical  (test)
    "trust_parliament",       # Q73  confidence, categorical  (test)
    "religiosity",            # Q164 importance of God 1-10   (fit)
    "religious_identity",     # Q173 religious/not/atheist    (test)
    "happiness",              # Q46  1 very happy .. 4 not at all happy  (fit)
    "life_satisfaction",      # Q49  1 dissatisfied .. 10 satisfied      (test)
    "income_equality",        # Q106 1 more equal .. 10 larger diffs     (fit)
    "competition",            # Q109 1 good .. 10 harmful                (test)
    "political_leaning",      # Q240 1 left .. 10 right                  (test)
    "financial_satisfaction", # Q50  1 not at all .. 10 completely       (test)
)

# Each held-out field's role: "fit" items may be used to calibrate; "test"
# items are reserved for measuring accuracy (never used to fit).
HELDOUT_ROLE = {
    "trust_government": "fit", "trust_courts": "fit",
    "trust_police": "test", "trust_parliament": "test",
    "religiosity": "fit", "religious_identity": "test",
    "happiness": "fit", "life_satisfaction": "test",
    "income_equality": "fit", "competition": "test",
    "political_leaning": "test", "financial_satisfaction": "test",
}

RUN_TYPES = ("probe", "scenario")
ARMS = ("treatment", "placebo", "vanilla")
MIN_CELL_N = 30
SATURATION = (0.10, 0.90)  # placebo share outside this band can't show an effect (rule 7)
