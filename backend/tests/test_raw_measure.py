"""Cached percentile summaries must never leak into the raw IF public contract."""

from decimal import Decimal

from licita_backend.repositories.process_analysis import raw_summary


def test_cached_percentiles_and_bounds_are_rebuilt_from_raw_points():
    row = {
        "id": "summary",
        "modelo_id": "forest",
        "algoritmo": "isolation_forest",
        "status": "parcial",
        "motivo": "COBERTURA_INSUFICIENTE",
        "score": None,
        "indice_observado": Decimal(99),
        "limite_inferior": 50,
        "limite_superior": 100,
        "cobertura": {"itens_oficiais": 3},
        "contexto": {},
        "sinais": {
            "itens": [
                {
                    "item_id": "one",
                    "media_observada": "100",
                    "contribuicao_observada": "50",
                    "resultados": [
                        {"resultado_modelo_id": "a", "indice": "100"},
                        {"resultado_modelo_id": "b", "indice": "100"},
                    ],
                },
                {
                    "item_id": "two",
                    "media_observada": "98",
                    "resultados": [{"resultado_modelo_id": "c", "indice": "98"}],
                },
            ]
        },
    }
    result = raw_summary(row, {"a": Decimal("0.4"), "b": Decimal("0.8"), "c": Decimal("0.2")})
    assert result["medida_if_observada"] == Decimal("0.4")
    assert result["medida_if_processo"] is None
    assert result["limite_inferior"] is result["limite_superior"] is None
    assert result["sinais"]["itens"][0]["media_observada"] == "0.6"
    assert "contribuicao_observada" not in result["sinais"]["itens"][0]
    assert all("indice" not in r for i in result["sinais"]["itens"] for r in i["resultados"])
    assert "score_processo" not in result and "indice_observado" not in result
