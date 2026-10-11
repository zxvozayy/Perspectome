"""Shared categories for every track. Change only via PR, with a heads-up to all tracks."""

AGE_BANDS = ("18-24", "25-34", "35-44", "45-54", "55-64", "65+")
GENDERS = ("male", "female")
EDUCATION_LEVELS = ("primary", "secondary", "vocational", "bachelor", "graduate")
SETTLEMENT_TYPES = ("urban", "rural")
MARITAL_STATUSES = ("married", "single", "divorced", "widowed")
EMPLOYMENT_STATUSES = ("employed", "unemployed", "student", "retired", "homemaker")
INCOME_DECILES = tuple(range(1, 11))

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

# Never visible to persona generation or simulation; validation only.
HELDOUT_FIELDS = (
    "political_leaning",
    "trust_institutions",
    "religiosity",
    "economic_optimism",
    "risk_tolerance",
)

RUN_TYPES = ("probe", "scenario")
ARMS = ("treatment", "placebo", "vanilla")
MIN_CELL_N = 30
