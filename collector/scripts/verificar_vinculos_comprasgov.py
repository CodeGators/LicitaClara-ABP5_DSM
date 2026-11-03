"""Confere granularidade e catálogo por identificador nos ZIPs do diagnóstico.

Uso: python3 collector/scripts/verificar_vinculos_comprasgov.py --entrada data/diagnostico/compras/2026-09
"""
import argparse
import csv
import hashlib
import io
import json
from collections import Counter
from pathlib import Path
from zipfile import ZipFile


def rows(path):
    with ZipFile(path) as archive:
        member = next(n for n in archive.namelist() if n.endswith('.csv'))
        with archive.open(member) as stream:
            yield from csv.DictReader(io.TextIOWrapper(stream, encoding='utf-8-sig'), delimiter=';')


def verify(folder, codigo):
    year, month = folder.name.split('-')
    paths = {name: folder / f'{name}_{year}_{month}.csv.zip' for name in ['compra', 'compra_item', 'item_resultado', 'material']}
    signatures = {}
    flags = Counter()
    for name, path in paths.items():
        seen, count = set(), 0
        for row in rows(path):
            count += 1
            digest = hashlib.sha256(json.dumps(row, ensure_ascii=False, sort_keys=True).encode()).digest()
            seen.add(digest)
            if name == 'compra':
                flags[row['ind_atual']] += 1
        signatures[name] = {'linhas': count, 'duplicatas_exatas': count - len(seen)}
    catalogue = {}
    conflicts = set()
    pilot_ids, pilot_companies, pilot_purchases, pilot_orgs = set(), set(), set(), set()
    pilot_rows = 0
    for row in rows(paths['material']):
        item, code = row['id_compra_item'], row['codigo_item_catalogo']
        if item in catalogue and catalogue[item] != code:
            conflicts.add(item)
        catalogue[item] = code
        if code == codigo and row['nome_unidade_fornecimento'] == 'UNIDADE' and row['capacidade_unidade_fornecimento'] == '0.00000000':
            pilot_ids.add(item)
            pilot_companies.add(row['ni_fornecedor'])
            pilot_purchases.add(row['id_compra'])
            pilot_orgs.add(row['codigo_orgao'])
            pilot_rows += 1
    common, linked_pilot = set(), set()
    for row in rows(paths['compra_item']):
        item = row['id_compra_item']
        if item in catalogue:
            common.add(item)
        if item in pilot_ids:
            linked_pilot.add(item)
    return {'por_arquivo': signatures, 'ind_atual_compras': dict(flags),
            'material_ids_com_codigos_catalogo_divergentes': len(conflicts),
            'ids_enriqueciveis_no_mes': len(common - conflicts),
            'piloto': {'catalogo': codigo, 'linhas': pilot_rows, 'ids_distintos': len(pilot_ids),
                       'compras_distintas': len(pilot_purchases), 'orgaos_distintos': len(pilot_orgs),
                       'fornecedores_distintos': len(pilot_companies),
                       'ids_com_item_pncp_no_mes': len(linked_pilot)}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--entrada', type=Path, required=True)
    parser.add_argument('--codigo-catalogo', default='486054')
    args = parser.parse_args()
    result = verify(args.entrada, args.codigo_catalogo)
    dest = args.entrada / 'vinculos.json'
    dest.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
