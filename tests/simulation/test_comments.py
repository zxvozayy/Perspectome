"""comments.py: persona comments on a free question, with a fake client (no network)."""

from types import SimpleNamespace

import pandas as pd

from src.common import paths, schema
from src.simulation import comments

PERSONA = {"persona_id": "s1", "age_band": "35-44", "gender": "female", "education_level": "secondary",
           "region": "Ic Anadolu", "settlement_type": "urban", "marital_status": "married",
           "employment_status": "employed", "income_decile": 3, "religiosity_band": "high",
           "political_leaning_band": "centre", "household_size": 4, "tenure": "tenant", "sector": "services",
           "informal": True, "concern": "cost_of_living", "internet_user": True, "genai_user": False}


class FakeClient:
    def __init__(self, replies):
        self.replies, self.requests = list(replies), []
        self.messages = self

    def create(self, **kwargs):
        self.requests.append(kwargs)
        text = self.replies.pop(0)
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)],
                               usage=SimpleNamespace(input_tokens=1, output_tokens=1))


def _frame(n):
    rows = [{**PERSONA, "persona_id": f"s{i}", "weight": 1.0, "cell_id": "x"} for i in range(n)]
    return pd.DataFrame(rows)


def test_prompt_describes_the_persona_and_never_a_heldout_item():
    text = comments.prompt(PERSONA, "Kira zammı?")
    assert "Kira zammı?" in text and "kirada oturuyor" in text and "İç Anadolu" in text
    assert "sigortasız" in text and "10 dilimden 3." in text
    for field in schema.HELDOUT_FIELDS:
        assert field not in text


def test_parse_reads_stance_and_comment():
    assert comments.parse("TUTUM: olumsuz\nYORUM: **Kira** çok arttı.") == ("OLUMSUZ", "Kira çok arttı.")
    assert comments.parse("I can't role-play this.") is None


def test_ask_drops_inconsistent_unreadable_and_repeated(tmp_path):
    path = tmp_path / "p.csv"
    _frame(5).to_csv(path, index=False)
    client = FakeClient([
        "TUTUM: OLUMSUZ\nYORUM: Kiradayım, her yıl zam geliyor, maaş yetmiyor.",
        "TUTUM: OLUMSUZ\nYORUM: Kendi evimde oturuyorum, beni etkilemez.",      # persona is a tenant
        "Sorry, I can't.",
        "TUTUM: KARARSIZ\nYORUM: Bilmiyorum, ev sahibi de zor durumda.",
        "TUTUM: OLUMSUZ\nYORUM: Kiradayım; her yıl zam geliyor, maaş yetmiyor!",  # same words as the first
    ])
    out = comments.ask("Kira zammı?", personas_path=path, n=5, client=client)
    assert [c["stance"] for c in out["comments"]] == ["OLUMSUZ", "KARARSIZ"]
    assert out["dropped"] == {"unreadable": 1, "inconsistent": 1, "duplicate": 1}
    assert out["stances"] == {"OLUMLU": 0, "OLUMSUZ": 1, "KARARSIZ": 1}
    assert all(r["thinking"] == {"type": "disabled"} for r in client.requests)
    assert "Kiracı" in out["comments"][0]["facts"]


def test_same_question_draws_the_same_people():
    personas = pd.read_csv(paths.PERSONAS_FIXTURE)
    a = comments.sample(personas, "Kira zammı?", 5)
    assert a.equals(comments.sample(personas, "  kira zammı?", 5))
    assert len(set(a["persona_id"])) == 5
