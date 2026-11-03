"""Baixa e perfila uma competência do repositório oficial; diagnóstico, não coletor de produção.

Uso: python3 collector/scripts/diagnosticar_comprasgov.py --ano 2026 --mes 9
Arquivos e perfis ficam em data/diagnostico/compras/<ano>-<mes>, fora do Git.
"""
import argparse
import csv
import hashlib
import io
import json
import time
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zipfile import ZipFile

BASE = 'https://repositorio.dados.gov.br/seges/comprasgov/'


def download(url, dest):
    meta = dest.with_suffix(dest.suffix + '.meta.json')
    if dest.exists() and meta.exists():
        saved = json.loads(meta.read_text())
        if hashlib.sha256(dest.read_bytes()).hexdigest() == saved['sha256']:
            return saved
    temp = dest.with_suffix('.part')
    for attempt in range(3):
        try:
            sha, size = hashlib.sha256(), 0
            with urllib.request.urlopen(url, timeout=45) as response, temp.open('wb') as out:
                for chunk in iter(lambda: response.read(1024 * 1024), b''):
                    size += len(chunk)
                    if size > 100 * 1024 * 1024:
                        raise ValueError('Diagnóstico limitado a 100 MiB por download.')
                    sha.update(chunk)
                    out.write(chunk)
                expected = response.headers.get('Content-Length')
                if expected and size != int(expected):
                    raise ValueError('Download incompleto.')
                final_url = response.url
            with ZipFile(temp) as archive:
                if archive.testzip() is not None:
                    raise ValueError('Falha de CRC no ZIP.')
            temp.replace(dest)
            saved = {'url': url, 'url_final': final_url, 'coletado_em': datetime.now(timezone.utc).isoformat(),
                     'bytes': size, 'sha256': sha.hexdigest(), 'arquivo': dest.name}
            meta.write_text(json.dumps(saved, ensure_ascii=False, indent=2) + '\n')
            return saved
        except Exception:
            temp.unlink(missing_ok=True)
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def download_segmentado(url, dest):
    """Fallback para conexões interrompidas; valida Range e ETag de cada bloco."""
    with urllib.request.urlopen(urllib.request.Request(url, method='HEAD'), timeout=30) as response:
        size = int(response.headers['Content-Length'])
        etag = response.headers.get('ETag')
    if size > 100 * 1024 * 1024 or not etag:
        raise ValueError('Download segmentado requer ETag e arquivo de até 100 MiB.')
    temp = dest.with_suffix('.part')
    sha = hashlib.sha256()
    with temp.open('wb') as out:
        for start in range(0, size, 1024 * 1024):
            end = min(start + 1024 * 1024, size) - 1
            for attempt in range(3):
                try:
                    req = urllib.request.Request(url, headers={'Range': f'bytes={start}-{end}', 'If-Match': etag})
                    with urllib.request.urlopen(req, timeout=30) as response:
                        if response.status != 206 or response.headers.get('Content-Range') != f'bytes {start}-{end}/{size}' or response.headers.get('ETag') != etag:
                            raise ValueError('Resposta parcial ou versão inesperada.')
                        chunk = response.read(end - start + 2)
                    if len(chunk) != end - start + 1:
                        raise ValueError('Bloco incompleto.')
                    out.write(chunk)
                    sha.update(chunk)
                    break
                except Exception:
                    if attempt == 2:
                        raise
                    time.sleep(2 ** attempt)
    with ZipFile(temp) as archive:
        if archive.testzip() is not None:
            raise ValueError('Falha de CRC no ZIP segmentado.')
    temp.replace(dest)
    metadata = {'url': url, 'url_final': url, 'coletado_em': datetime.now(timezone.utc).isoformat(),
                'bytes': size, 'sha256': sha.hexdigest(), 'arquivo': dest.name, 'etag': etag, 'modo': 'range_1MiB'}
    dest.with_suffix(dest.suffix + '.meta.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n')
    return metadata


def profile(dest, name):
    stats = {'arquivo': dest.name, 'tabelas': []}
    ids, parents = set(), set()
    categories = Counter()
    with ZipFile(dest) as archive:
        for entry in archive.infolist():
            if not entry.filename.endswith('.csv'):
                continue
            missing, count, dates, numeric_zero, sample = Counter(), 0, {}, Counter(), []
            with archive.open(entry) as stream:
                reader = csv.DictReader(io.TextIOWrapper(stream, encoding='utf-8-sig', newline=''), delimiter=';')
                columns = reader.fieldnames
                for row in reader:
                    if None in row or None in row.values():
                        raise ValueError(f'Quantidade de campos inválida em {entry.filename}')
                    count += 1
                    for key, val in row.items():
                        if not val.strip():
                            missing[key] += 1
                        if key.startswith('data_') and val.strip():
                            prev = dates.get(key)
                            dates[key] = [min(prev[0], val), max(prev[1], val)] if prev else [val, val]
                        if key.startswith(('valor_', 'quantidade', 'preco_')) and val.strip():
                            try:
                                if Decimal(val) == 0:
                                    numeric_zero[key] += 1
                            except InvalidOperation:
                                raise ValueError(f'Decimal inválido na coluna {key}')
                    primary = row.get('id_compra_item') if name != 'compra' else row.get('id_compra')
                    if primary:
                        ids.add(primary)
                    if row.get('id_compra'):
                        parents.add(row['id_compra'])
                    if name == 'material':
                        category = (row.get('codigo_item_catalogo', ''), row.get('descricao_item', ''),
                                    row.get('nome_unidade_fornecimento', ''), row.get('sigla_unidade_fornecimento', ''))
                        categories[category] += 1
                    if len(sample) < 5:
                        sample.append({k: v for k, v in row.items() if any(t in k for t in ['catalogo', 'unidade', 'descricao_item'])})
            stats['tabelas'].append({'membro': entry.filename, 'bytes_csv': entry.file_size, 'linhas': count,
                                     'colunas': columns, 'vazios': {c: missing[c] for c in columns},
                                     'zeros_numericos': dict(numeric_zero), 'intervalos_datas_textuais': dates,
                                     'amostra_campos_catalogo_unidade': sample})
    if categories:
        stats['categorias_mais_frequentes'] = [{'codigo': k[0], 'descricao': k[1], 'unidade': k[2], 'sigla': k[3], 'linhas': v} for k, v in categories.most_common(15)]
    stats['ids_distintos_nao_vazios'] = len(ids)
    return stats, ids, parents


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ano', type=int, required=True)
    parser.add_argument('--mes', type=int, choices=range(1, 13), required=True)
    parser.add_argument('--blocos', action='store_true', help='Usar Range e ETag em downloads novos.')
    parser.add_argument('--destino', type=Path, default=Path('data/diagnostico/compras'))
    args = parser.parse_args()
    folder = args.destino / f'{args.ano}-{args.mes:02}'
    folder.mkdir(parents=True, exist_ok=True)
    def fetch(name):
        module = 'pesquisa_precos' if name == 'material' else 'pncp'
        filename = f'{name}_{args.ano}_{args.mes:02}.csv.zip'
        dest = folder / filename
        url = f'{BASE}{module}/{args.ano}/{args.mes:02}/{filename}'
        meta = download_segmentado(url, dest) if args.blocos and not dest.exists() else download(url, dest)
        print(f'{name}: download validado, {meta["bytes"]} bytes', flush=True)
        stats, ids, parents = profile(dest, name)
        print(f'{name}: perfil concluído', flush=True)
        return name, meta, stats, ids, parents
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(fetch, ['compra', 'compra_item', 'item_resultado', 'material']))
    stats = {name: {'download': meta, 'perfil': prof} for name, meta, prof, _, _ in results}
    ids = {r[0]: r[3] for r in results}
    parents = {r[0]: r[4] for r in results}
    stats['relacoes'] = {'itens_sem_compra': len(parents['compra_item'] - ids['compra']),
                         'resultados_sem_compra': len(parents['item_resultado'] - ids['compra']),
                         'ids_resultado_sem_item': len(ids['item_resultado'] - ids['compra_item']),
                         'material_ids_com_item_pncp_no_mes': len(ids['material'] & ids['compra_item']),
                         'material_ids_distintos': len(ids['material'])}
    (folder / 'perfil.json').write_text(json.dumps(stats, ensure_ascii=False, indent=2) + '\n')
    print(f'Diagnóstico salvo em {folder / "perfil.json"}', flush=True)


if __name__ == '__main__':
    main()
