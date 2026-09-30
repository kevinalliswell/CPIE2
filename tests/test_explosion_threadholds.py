"""Configured explosion thresholds must classify every boundary correctly."""
import pytest
from models.explosion_database import ExplosionDatabase


@pytest.mark.parametrize('length, expected', [
    (15.0, '无爆炸性'), (24.9, '无爆炸性'), (25.0, '弱爆炸性'),
    (100.0, '弱爆炸性'), (399.9, '弱爆炸性'), (400.0, '强爆炸性'),
    (600.0, '强爆炸性'), (799.9, '强爆炸性'), (800.0, '超强爆炸性'),
    (1000.0, '超强爆炸性'),
])
def test_threshold_loading(tmp_path, length, expected):
    db = ExplosionDatabase(str(tmp_path / 'thresholds.db'))
    try:
        assert db.classify_explosion_strength(length) == expected
    finally:
        db.close()
