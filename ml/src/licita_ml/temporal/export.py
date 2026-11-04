"""Exportação das matrizes com números finitos; IDs são somente rastreabilidade."""

import csv
import math
from datetime import date

import pyarrow as pa
import pyarrow.parquet as pq

from licita_ml.organized.schema import TYPES, Export


class NumericExport(Export):
    def __init__(self, folder, name, fields):
        self.name, self.fields, self.count, self.buffer = name, fields, 0, []
        types = {**TYPES, "real": pa.float64()}
        self.schema = pa.schema([(field, types[kind]) for field, kind in fields.items()])
        self.parquet = pq.ParquetWriter(folder / f"{name}.parquet", self.schema, compression="zstd")
        self.stream = (folder / f"{name}.csv").open("w", encoding="utf-8", newline="")
        self.csv = csv.DictWriter(self.stream, fieldnames=list(fields), delimiter=";")
        self.csv.writeheader()

    def add(self, row):
        row = dict(row)
        for field, kind in self.fields.items():
            if kind == "data" and isinstance(row.get(field), date):
                row[field] = row[field].isoformat()
        for field, kind in self.fields.items():
            if kind == "real" and row.get(field) is not None and not math.isfinite(row[field]):
                raise ValueError("Matriz contém número não finito")
        super().add(row)
