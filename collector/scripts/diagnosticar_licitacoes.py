"""Diagnóstico local de ZIPs já baixados; não é o coletor de produção.

Uso: python collector/scripts/diagnosticar_licitacoes.py --entrada data/diagnostico
Para medir Parquet, instalar pyarrow e passar --parquet.
Não extrai arquivos nem grava identificadores pessoais no resumo.
"""
import argparse
import csv
import hashlib
import io
import json
from collections import Counter
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zipfile import ZipFile


def numero(value):
    return Decimal(value.replace('.', '').replace(',', '.'))


def analisar(path, parquet):
    result = {'arquivo': path.name, 'bytes_zip': path.stat().st_size,
              'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'tabelas': {}}
    datasets = {}
    with ZipFile(path) as archive:
        for entry in archive.infolist():
            if not entry.filename.endswith('.csv'):
                continue
            # Lê o membro em memória, sem extrair caminhos do ZIP.
            text = archive.read(entry).decode('cp1252')
            reader = csv.DictReader(io.StringIO(text), delimiter=';')
            rows = list(reader)
            columns = reader.fieldnames
            if any(None in row or None in row.values() for row in rows):
                raise ValueError(f'Linha com número inesperado de campos: {entry.filename}')
            kind = entry.filename.split('_', 1)[1].removesuffix('.csv')
            datasets[kind] = rows
            stats = {'linhas': len(rows), 'bytes_csv': entry.file_size,
                     'encoding_leitura': 'cp1252', 'delimitador': ';', 'colunas': columns,
                     'duplicatas_linha': len(rows) - len({tuple(row.values()) for row in rows}),
                     'vazios_por_coluna': {col: sum(not row[col].strip() for row in rows) for col in columns}}
            for col in columns:
                if col.startswith('Data '):
                    valid, invalid = [], 0
                    for row in rows:
                        if row[col].strip():
                            try:
                                valid.append(datetime.strptime(row[col], '%d/%m/%Y').date().isoformat())
                            except ValueError:
                                invalid += 1
                    stats[col] = {'min': min(valid, default=None), 'max': max(valid, default=None), 'invalidos': invalid}
                if col in ('Quantidade Item', 'Valor Item', 'Valor Licitação', 'Valor Empenho (R$)'):
                    values, invalid = [], 0
                    for row in rows:
                        if row[col].strip():
                            try:
                                value = numero(row[col])
                                if not value.is_finite():
                                    raise InvalidOperation
                                values.append(value)
                            except InvalidOperation:
                                invalid += 1
                    stats[col] = {'invalidos': invalid, 'zeros': sum(x == 0 for x in values),
                                  'negativos': sum(x < 0 for x in values),
                                  'min': str(min(values)) if values else None,
                                  'max': str(max(values)) if values else None}
            if parquet:
                import pyarrow as pa
                import pyarrow.parquet as pq
                dest = path.parent / 'parquet' / path.stem / (kind + '.parquet')
                dest.parent.mkdir(parents=True, exist_ok=True)
                table = pa.table({col: pa.array([row[col] for row in rows], type=pa.string()) for col in columns})
                pq.write_table(table, dest, compression='zstd')
                stats['bytes_parquet_strings'] = dest.stat().st_size
            result['tabelas'][kind] = stats
    processes = datasets['Licitação']
    items = datasets['ItemLicitação']
    participants = datasets['ParticipantesLicitação']
    keycols = ['Código UG', 'Código Modalidade Compra', 'Número Licitação']
    def key(row):
        return tuple(row[col] for col in keycols)
    keys = {key(row) for row in processes}
    item_ids = {row['Código Item Compra'] for row in items}
    result['relacoes'] = {
        'chave_processo_candidata': keycols,
        'duplicatas_chave_processo': len(processes) - len(keys),
        'itens_sem_processo_na_competencia': sum(key(row) not in keys for row in items),
        'participacoes_sem_processo_na_competencia': sum(key(row) not in keys for row in participants),
        'participacoes_sem_item_na_competencia': sum(row['Código Item Compra'] not in item_ids for row in participants),
        'itens_distintos': len(item_ids),
        'linhas_item_com_codigo_repetido': len(items) - len(item_ids),
        'duplicatas_item_vencedor': len(items) - len({(row['Código Item Compra'], row['Código Vencedor']) for row in items}),
        'duplicatas_item_participante': len(participants) - len({(row['Código Item Compra'], row['Código Participante']) for row in participants}),
        'orgaos_distintos_processos': len({row['Código Órgão'] for row in processes}),
        'vencedores_distintos_itens': len({row['Código Vencedor'] for row in items if row['Código Vencedor'].strip()}),
        'itens_codigo_diferente_22_digitos': sum(not (row['Código Item Compra'].isdigit() and len(row['Código Item Compra']) == 22) for row in items),
        'flag_vencedor': dict(Counter(row['Flag Vencedor'] for row in participants)),
        'modalidades_processos': dict(Counter(row['Modalidade Compra'] for row in processes)),
    }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--entrada', type=Path, required=True)
    parser.add_argument('--parquet', action='store_true')
    args = parser.parse_args()
    paths = sorted(args.entrada.glob('*_Licitacoes.zip'))
    if not paths:
        parser.error('Nenhum ZIP encontrado no diretório de entrada.')
    result = [analisar(path, args.parquet) for path in paths]
    dest = args.entrada / 'perfil.json'
    dest.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(f'Resumo de {len(result)} arquivos gravado em {dest}')


if __name__ == '__main__':
    main()
