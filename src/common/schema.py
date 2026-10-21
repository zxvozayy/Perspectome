"""Shared categories for every track. Change only via PR, with a heads-up to all tracks."""

AGE_BANDS = ("18-24", "25-34", "35-44", "45-54", "55-64", "65+")
AGE_EDGES = (18, 25, 35, 45, 55, 65)  # lower bound (years) of each AGE_BANDS entry
GENDERS = ("male", "female")
EDUCATION_LEVELS = ("primary", "secondary", "vocational", "bachelor", "graduate")
SETTLEMENT_TYPES = ("urban", "rural")
MARITAL_STATUSES = ("married", "single", "divorced", "widowed")
EMPLOYMENT_STATUSES = ("employed", "unemployed", "student", "retired", "homemaker")
INCOME_DECILES = tuple(range(1, 11))
# The 7 geographic regions; the 12 NUTS-1 regions collapse onto these (personas/sources/wvs.py).
REGIONS = ("Marmara", "Ege", "Akdeniz", "Ic Anadolu", "Karadeniz", "Dogu Anadolu", "Guneydogu Anadolu")
# WVS Q164 importance of God: 1-4 low, 5-7 medium, 8-9 high, 10 very_high.
RELIGIOSITY_BANDS = ("low", "medium", "high", "very_high")
# WVS Q240 left-right self-placement: 1-4 left, 5-6 centre, 7-10 right.
POLITICAL_BANDS = ("left", "centre", "right")

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
    "religiosity_band",
    "political_leaning_band",
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
    "religiosity_band": RELIGIOSITY_BANDS,
    "political_leaning_band": POLITICAL_BANDS,
}

# personas.csv columns, in contract order.
PERSONA_COLUMNS = ("persona_id", "cell_id", "weight", *CONDITIONING_FIELDS[1:])

# Extra fields carried only by the synthetic persona set (personas_synthetic.csv),
# attached after generation. Layer: L1 household/work (from LiTS IV donors),
# L3 lifestyle (published tables), L4 concerns (published tables).
TENURES = ("owner", "tenant", "rent_free")
SECTORS = ("agriculture", "industry", "construction", "services", "public")
SYNTHETIC_FIELDS = {
    "household_size": "L1", "tenure": "L1", "sector": "L1", "informal": "L1",
    "smoker": "L3", "drinks_alcohol": "L3", "obese": "L3", "internet_user": "L3", "genai_user": "L3",
    "concern": "L4",
}

# The fields that define an archetype cell (cell_id = "age_band|gender|education_level").
CELL_FIELDS = ("age_band", "gender", "education_level")

# Never visible to persona generation or simulation; validation only (Track C).
# Two items per topic -- one to FIT (calibrate) and one to TEST (measure
# accuracy) -- so accuracy is measured on items that never touched calibration.
# Religiosity (Q164) and left-right (Q240) moved to the conditioning fields on
# 2026-10-21 (project-lead decision); Q173 left with them because it is a
# near-duplicate of Q164. Every item below is checked against the WVS-7
# codebook (Variables report v6.0) and asked in the Türkiye file.
HELDOUT_FIELDS = (
    "trust_government",        # Q71  confidence, categorical               (fit)
    "trust_courts",            # Q70  confidence, categorical               (fit)
    "trust_police",            # Q69  confidence, categorical               (test)
    "trust_parliament",        # Q73  confidence, categorical               (test)
    "happiness",               # Q46  1 very happy .. 4 not at all happy    (fit)
    "life_satisfaction",       # Q49  1 dissatisfied .. 10 satisfied         (test)
    "income_equality",         # Q106 1 more equal .. 10 larger differences  (fit)
    "competition",             # Q109 1 good .. 10 harmful                   (test)
    "financial_satisfaction",  # Q50  1 not at all .. 10 completely          (test)
    "gender_jobs",             # Q33  men more right to scarce jobs, 1 agree strongly .. 5 disagree strongly  (fit)
    "gender_income",           # Q35  wife earning more causes problems, same 5-point scale                  (test)
    "immigrant_jobs",          # Q34  nationals first for scarce jobs, same 5-point scale                    (test)
    "science_life",            # Q158 science makes life easier, 1 completely disagree .. 10 completely agree (fit)
    "science_future",          # Q159 science brings opportunities to the next generation, same scale         (test)
)

# Each held-out field's role: "fit" items may be used to calibrate; "test"
# items are reserved for measuring accuracy (never used to fit).
HELDOUT_ROLE = {
    "trust_government": "fit", "trust_courts": "fit",
    "trust_police": "test", "trust_parliament": "test",
    "happiness": "fit", "life_satisfaction": "test",
    "income_equality": "fit", "competition": "test",
    "financial_satisfaction": "test",
    "gender_jobs": "fit", "gender_income": "test", "immigrant_jobs": "test",
    "science_life": "fit", "science_future": "test",
}

RUN_TYPES = ("probe", "scenario")
ARMS = ("treatment", "placebo", "vanilla")
MIN_CELL_N = 30
SATURATION = (0.10, 0.90)  # placebo share outside this band can't show an effect (rule 7)
