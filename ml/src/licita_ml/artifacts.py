import hashlib
import io

import pyarrow as pa
import pyarrow.parquet as pq
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from licita_ml.staging import encode


def parquet_bytes(table, rows):
    keys = set().union(*(r.keys() for r in rows))
    fields = []
    arrays = []
    for column in table.columns:
        if column.name not in keys:
            continue
        t = column.type
        if isinstance(t, sa.Numeric):
            arrow = pa.decimal128(t.precision, t.scale)
        elif isinstance(t, sa.Boolean):
            arrow = pa.bool_()
        elif isinstance(t, sa.DateTime):
            arrow = pa.timestamp("us", tz="UTC" if t.timezone else None)
        elif isinstance(t, sa.Date):
            arrow = pa.date32()
        elif isinstance(t, (sa.Integer, sa.BigInteger)):
            arrow = pa.int64()
        else:
            arrow = pa.string()
        values = [r.get(column.name) for r in rows]
        if isinstance(t, (JSONB, UUID)):
            values = [
                None if v is None else encode(v) if isinstance(t, JSONB) else str(v) for v in values
            ]
        fields.append(pa.field(column.name, arrow, nullable=column.nullable))
        arrays.append(pa.array(values, type=arrow))
    batch = pa.Table.from_arrays(arrays, schema=pa.schema(fields))
    output = pa.BufferOutputStream()
    pq.write_table(batch, output, compression="zstd", version="2.6")
    return output.getvalue().to_pybytes(), str(batch.schema)


def publish(objects, repository, data, stage, prefix, manifest):
    outputs = []
    for name, rows in sorted(data.items()):
        if not rows:
            continue
        raw, schema = parquet_bytes(repository.tables[name], rows)
        key = f"{prefix}/entidade={name}/part-00000.parquet"
        stored = objects.put(key, io.BytesIO(raw))
        outputs.append(
            {
                "tabela": name,
                "chave": key,
                "sha256": stored.sha256,
                "bytes": stored.size_bytes,
                "linhas": len(rows),
                "esquema_arrow": schema,
            }
        )
    rejects = "".join(encode(row) + "\n" for row in sorted(stage.rejects, key=encode)).encode()
    rejected = objects.put(prefix + "/rejeicoes.jsonl", io.BytesIO(rejects))
    manifest["arquivos_parquet"] = outputs
    manifest["rejeicoes"] = {
        "chave": rejected.key,
        "sha256": rejected.sha256,
        "bytes": rejected.size_bytes,
        "linhas": len(stage.rejects),
    }
    raw = (encode(manifest) + "\n").encode()
    key = prefix + "/manifesto.json"
    stored = objects.put(key, io.BytesIO(raw))
    assert stored.sha256 == hashlib.sha256(raw).hexdigest()
    return stored, manifest
