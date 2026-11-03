"""Amostra limitada da API oficial; uma página por domínio e vínculos de um exemplo.

Uso: python3 collector/scripts/amostrar_api_comprasgov.py --inicio 2026-09-01 --fim 2026-09-30
Não representa cobertura integral ou seleção aleatória.
"""
import argparse
import hashlib
import json
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from pathlib import Path

BASE = 'https://dadosabertos.compras.gov.br'


def request(name, path, params, dest):
    url = BASE + path + '?' + urllib.parse.urlencode(params)
    with urllib.request.urlopen(urllib.request.Request(url, headers={'Accept': 'application/json'}), timeout=60) as response:
        raw = response.read(12 * 1024 * 1024 + 1)
        if len(raw) > 12 * 1024 * 1024:
            raise ValueError('Resposta excede limite do diagnóstico de 12 MiB.')
        metadata = {'url': url, 'status': response.status, 'content_type': response.headers.get('Content-Type'),
                    'coletado_em': datetime.now(timezone.utc).isoformat(), 'bytes': len(raw),
                    'sha256': hashlib.sha256(raw).hexdigest()}
    payload = json.loads(raw)
    if not isinstance(payload.get('resultado'), list):
        raise ValueError('Formato inesperado de resultado.')
    (dest / f'{name}.json').write_bytes(raw)
    (dest / f'{name}.meta.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n')
    rows = payload['resultado']
    summary = {'requisicao': metadata, 'linhas_amostradas': len(rows),
               'total_informado_api': payload.get('totalRegistros'),
               'campos': sorted({key for row in rows for key in row}),
               'ausentes_por_campo': {key: sum(row.get(key) in (None, '') for row in rows) for key in sorted({k for row in rows for k in row})}}
    print(f'{name}: {len(rows)} registros recebidos', flush=True)
    return rows, summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inicio', type=date.fromisoformat, required=True)
    parser.add_argument('--fim', type=date.fromisoformat, required=True)
    parser.add_argument('--codigo-catalogo', type=int, help='Validar um CATMAT e seus preços no período.')
    parser.add_argument('--destino', type=Path, default=Path('data/diagnostico/compras/api'))
    args = parser.parse_args()
    if args.inicio > args.fim:
        parser.error('Data inicial posterior à final.')
    args.destino.mkdir(parents=True, exist_ok=True)
    interval = [args.inicio.isoformat(), args.fim.isoformat()]
    queries = [
        ('contratacoes', '/modulo-contratacoes/1_consultarContratacoes_PNCP_14133',
         {'dataPublicacaoPncpInicial': interval[0], 'dataPublicacaoPncpFinal': interval[1], 'codigoModalidade': 6}),
        ('itens', '/modulo-contratacoes/2_consultarItensContratacoes_PNCP_14133',
         {'dataInclusaoPncpInicial': interval[0], 'dataInclusaoPncpFinal': interval[1], 'materialOuServico': 'M', 'temResultado': 'true'}),
        ('resultados', '/modulo-contratacoes/3_consultarResultadoItensContratacoes_PNCP_14133',
         {'dataResultadoPncpInicial': interval[0], 'dataResultadoPncpFinal': interval[1]})]
    def fetch(query):
        name, path, params = query
        return name, request(name, path, dict(params, pagina=1, tamanhoPagina=100), args.destino)
    with ThreadPoolExecutor(max_workers=2) as executor:
        replies = dict(executor.map(fetch, queries))
    summary = {name: value[1] for name, value in replies.items()}
    if replies['itens'][0]:
        first = replies['itens'][0][0]
        for name, endpoint in [('compra_vinculada', '1.1_consultarContratacoes'), ('resultados_vinculados', '3.1_consultarResultadoItensContratacoes')]:
            _, stats = request(name, f'/modulo-contratacoes/{endpoint}_PNCP_14133_Id',
                               {'tipo': 'idCompra', 'codigo': first['idCompra']}, args.destino)
            summary[name] = stats
    if args.codigo_catalogo is not None:
        for name, path, params in [
            (f'catalogo_{args.codigo_catalogo}', '/modulo-material/4_consultarItemMaterial',
             {'codigoItem': args.codigo_catalogo, 'pagina': 1, 'tamanhoPagina': 100}),
            (f'precos_{args.codigo_catalogo}', '/modulo-pesquisa-preco/1_consultarMaterial',
             {'tipo': 'codigoItemCatalogo', 'codigo': args.codigo_catalogo,
              'dataCompraInicio': interval[0], 'dataCompraFim': interval[1], 'pagina': 1, 'tamanhoPagina': 100})]:
            _, stats = request(name, path, params, args.destino)
            summary[name] = stats
    (args.destino / 'perfil_api.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
