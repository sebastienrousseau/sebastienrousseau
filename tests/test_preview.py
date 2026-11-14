"""make preview writes a gallery of every hero with its clock running."""

from __future__ import annotations

import json

import holidays
import preview


def test_the_gallery_has_every_hero_running_and_every_theme(tmp_path):
    assert preview.main(["preview", str(tmp_path)]) == 0
    heroes = sorted((tmp_path / "heroes").glob("*.svg"))
    years, hs = holidays.load()
    assert len(heroes) == 2 * (len(hs) + 1)
    assert (tmp_path / "heroes" / "default-light.svg").exists()
    for path in heroes[:4]:
        text = path.read_text()
        assert preview.RUNNING in text and "/*clock*/" not in text
    page = (tmp_path / "index.html").read_text()
    data = json.loads(page.split("const DATA = ")[1].split(";\n")[0])
    assert [d["key"] for d in data] == ["default", *(h.key for h in hs)]
    vesak = next(d for d in data if d["key"] == "vesak")
    assert vesak["when"] == "table 1 (no sourced date for 2026, 2027, 2028, 2029, 2030)"
