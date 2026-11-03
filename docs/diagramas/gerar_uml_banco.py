"""Gera UML local a partir da metadata; executar com uv run --all-packages python este_arquivo."""
import html
import json
from pathlib import Path

from sqlalchemy.dialects.postgresql import dialect

from licita_backend.models import Base

ROOT = Path(__file__).resolve().parent
GROUPS = [
    ("Coleta e bases", ["execucoes_coleta", "arquivos_coletados", "execucoes_arquivos", "importacoes", "versoes_base", "base_importacoes"]),
    ("Cadastros e identidades", ["orgaos", "fornecedores", "modalidades", "itens_catalogo", "processos", "itens_processo", "contratos"]),
    ("Compras e propostas", ["processos_versoes", "itens_versoes", "resultados_itens", "referencias_precos", "participacoes"]),
    ("Contratos e proveniência", ["contratos_versoes", "contratos_processos", "documentos", "proveniencias_registros"]),
    ("Modelos e análises", ["versoes_modelo", "execucoes_analise", "execucoes_modelos", "resultados_modelo", "avaliacoes_processo", "comparacoes_itens", "comparacoes_referencias", "fatores_sinalizacao"]),
    ("Publicação e revisão", ["publicacoes_analise", "usuarios", "revisoes", "relatorios"]),
]
COLORS = ["#0f766e", "#2563eb", "#7c3aed", "#b45309", "#be185d", "#475569"]


def main():
    tables = Base.metadata.tables
    assert {name for _, names in GROUPS for name in names} == set(tables)
    entities, relations = {}, []
    for table in tables.values():
        columns = []
        for col in table.columns:
            columns.append({"name": col.name, "type": str(col.type.compile(dialect=dialect())),
                            "pk": col.primary_key, "fk": bool(col.foreign_keys), "nullable": col.nullable})
        entities[table.name] = {"columns": columns, "domain": table.info.get("domain")}
        for fk in table.foreign_key_constraints:
            local = list(fk.columns)
            parent = fk.referred_table
            # Cada linha filha aponta para 1 pai, ou 0..1 quando a FK é opcional.
            # 0..* é uma cardinalidade permissiva; restrições UNIQUE refinam por base.
            optional = any(col.nullable for col in local)
            relations.append({"child": table.name, "parent": parent.name,
                              "columns": [c.name for c in local],
                              "references": [element.column.name for element in fk.elements],
                              "parent_cardinality": "0..1" if optional else "1"})
    uml = ["@startuml", "title Licita Clara — PostgreSQL (34 tabelas)", "hide methods",
           "skinparam classAttributeIconSize 0", "skinparam linetype ortho", "left to right direction"]
    for index, (label, names) in enumerate(GROUPS):
        uml.append(f'package "{label}" {COLORS[index]} {{')
        for name in names:
            uml.append(f'class {name} <<table>> {{')
            for col in entities[name]["columns"]:
                keys = ','.join(k for k in ["PK" if col["pk"] else "", "FK" if col["fk"] else ""] if k)
                uml.append(f'  {col["name"]} : {col["type"]}{" ["+keys+"]" if keys else ""}{" ?" if col["nullable"] else ""}')
            uml.append('}')
        uml.append('}')
    for rel in relations:
        uml.append(f'{rel["parent"]} "{rel["parent_cardinality"]}" -- "0..*" {rel["child"]} : {", ".join(rel["columns"])}')
    uml.append('@enduml')
    (ROOT / 'UML_BANCO.puml').write_text('\n'.join(uml)+'\n')

    width = 6 * 350 + 40
    positions, boxes = {}, []
    for index, (label, names) in enumerate(GROUPS):
        x, y = 20 + index * 350, 100
        boxes.append(f'<text x="{x}" y="75" class="group">{html.escape(label)}</text>')
        for name in names:
            data = entities[name]
            # Visão geral compacta; lista integral no painel HTML e no PlantUML.
            chosen = [c for c in data['columns'] if c['pk'] or c['fk']]
            chosen += [c for c in data['columns'] if c not in chosen][:3]
            more = len(data['columns']) - len(chosen)
            height = 44 + 19 * (len(chosen) + bool(more))
            positions[name] = (x, y, 325, height)
            lines = [f'<g class="entity" data-name="{name}" tabindex="0" role="button" aria-label="Tabela {name}">',
                     f'<rect x="{x}" y="{y}" width="325" height="{height}" rx="7" fill="white" stroke="{COLORS[index]}"/>',
                     f'<rect x="{x}" y="{y}" width="325" height="30" rx="7" fill="{COLORS[index]}"/>',
                     f'<text x="{x+10}" y="{y+20}" class="title">{name}</text>']
            for row, col in enumerate(chosen):
                marks = ('PK ' if col['pk'] else '') + ('FK ' if col['fk'] else '')
                text = marks + col['name'] + (' ?' if col['nullable'] else '')
                lines.append(f'<text x="{x+10}" y="{y+48+row*19}" class="field">{html.escape(text)}</text>')
            if more:
                lines.append(f'<text x="{x+10}" y="{y+48+len(chosen)*19}" class="more">+ {more} campos no UML completo</text>')
            lines.append('</g>')
            boxes.extend(lines)
            y += height + 24
    height = max(y+h for x,y,w,h in positions.values())+30
    edges = []
    for index, rel in enumerate(relations):
        cx,cy,cw,ch = positions[rel['child']]
        px,py,pw,ph = positions[rel['parent']]
        if cx == px:
            sx, sy, tx, ty = cx+cw,cy+ch/2,px+pw,py+ph/2
            bend = sx+10+(index%3)*5
            path = f'M {sx} {sy} C {bend} {sy} {bend} {ty} {tx} {ty}'
        else:
            sx, tx = (cx,px+pw) if cx>px else (cx+cw,px)
            sy,ty = cy+ch/2,py+ph/2
            middle = (sx+tx)/2
            path = f'M {sx} {sy} C {middle} {sy} {middle} {ty} {tx} {ty}'
        description = f'{rel["child"]} ({", ".join(rel["columns"])}) → {rel["parent"]} ({", ".join(rel["references"])})'
        edges.append(f'<path class="edge" data-child="{rel["child"]}" data-parent="{rel["parent"]}" d="{path}" marker-end="url(#arrow)"><title>{html.escape(description)}</title></path>')
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<style>.group{{font:600 16px sans-serif;fill:#0f172a}} .title{{font:600 13px monospace;fill:white}} .field{{font:12px monospace;fill:#334155}} .more{{font:italic 11px sans-serif;fill:#64748b}} .edge{{fill:none;stroke:#64748b;stroke-width:1.3;opacity:.18}} .entity{{cursor:pointer}} .entity:focus rect{{stroke-width:3}} .dim{{opacity:.2}} .active-edge{{opacity:1;stroke:#0f766e;stroke-width:2.2}}</style>
<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#64748b"/></marker></defs>
<rect width="100%" height="100%" fill="#f8fafc"/>
<text x="20" y="30" class="group">Licita Clara — 34 tabelas • PK: chave primária • FK: chave estrangeira • ?: aceita NULL</text>
<text x="20" y="50" class="more">Setas apontam da tabela filha para a tabela referenciada. Abra o HTML para selecionar tabelas e consultar todos os campos.</text>
{''.join(edges)}{''.join(boxes)}</svg>'''
    (ROOT/'UML_BANCO.svg').write_text(svg)
    template = '''<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>UML — Licita Clara</title>
<style>body{margin:0;background:#f8fafc;color:#0f172a;font:14px system-ui}header{padding:15px 20px;background:white;border-bottom:1px solid #cbd5e1;display:flex;align-items:center;gap:12px;flex-wrap:wrap}h1{font-size:20px;margin:0}button,input{font:inherit;padding:7px;border:1px solid #94a3b8;border-radius:5px;background:white}button{cursor:pointer}main{display:grid;grid-template-columns:minmax(0,1fr) 370px;height:calc(100vh - 80px)}#canvas{overflow:auto}#diagram{width:max-content;transform-origin:top left}aside{padding:16px;overflow:auto;background:white;border-left:1px solid #cbd5e1}td,th{text-align:left;padding:6px;border-bottom:1px solid #e2e8f0;font-size:12px;overflow-wrap:anywhere}table{width:100%;border-collapse:collapse}code{font-size:12px}li{margin:8px 0}#name{overflow-wrap:anywhere}@media(max-width:800px){main{grid-template-columns:1fr;height:auto}#canvas{height:65vh}aside{border-top:1px solid #cbd5e1}}</style>
<header><h1>Banco Licita Clara · UML</h1><input id="search" aria-label="Buscar tabela" placeholder="Buscar tabela" list="tables"><datalist id="tables"></datalist><button id="minus">−</button><span id="scale">65%</span><button id="plus">+</button><button id="reset">Ver todas</button><a href="UML_BANCO.puml" download>PlantUML completo</a></header>
<main><div id="canvas"><div id="diagram">__SVG__</div></div><aside><h2 id="name">Selecione uma tabela</h2><p id="description">Clique em uma tabela para destacar seus vínculos e consultar todos os campos. Use a busca ou a rolagem para navegar. Funciona sem internet.</p><div id="details"></div></aside></main>
<script>const data=__DATA__;let zoom=.65;const $=id=>document.getElementById(id);function size(){ $('diagram').style.zoom=zoom;$('scale').textContent=Math.round(zoom*100)+'%';}size();$('plus').onclick=()=>{zoom=Math.min(2,zoom+.1);size()};$('minus').onclick=()=>{zoom=Math.max(.25,zoom-.1);size()};const escape=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function select(name){if(!data.entities[name])return;const links=data.relations.filter(r=>r.parent===name||r.child===name),near=new Set([name,...links.flatMap(r=>[r.parent,r.child])]);document.querySelectorAll('.entity').forEach(e=>e.classList.toggle('dim',!near.has(e.dataset.name)));document.querySelectorAll('.edge').forEach(e=>{const active=e.dataset.parent===name||e.dataset.child===name;e.classList.toggle('active-edge',active);e.classList.toggle('dim',!active)});$('name').textContent=name;$('description').textContent='Domínio: '+data.entities[name].domain+' · '+data.entities[name].columns.length+' campos';$('details').innerHTML='<table><tr><th>Campo</th><th>Tipo</th><th>Chaves / NULL</th></tr>'+data.entities[name].columns.map(c=>'<tr><td>'+escape(c.name)+'</td><td>'+escape(c.type)+'</td><td>'+[c.pk?'PK':'',c.fk?'FK':'',c.nullable?'NULL':'NOT NULL'].filter(Boolean).join(' · ')+'</td></tr>').join('')+'</table><h3>Relacionamentos físicos</h3><ul>'+links.map(r=>'<li><code>'+escape(r.child+' ('+r.columns.join(', ')+') → '+r.parent+' ('+r.references.join(', ')+')')+'</code><br>Pai por registro filho: '+r.parent_cardinality+'</li>').join('')+'</ul><p>FK composta é um único vínculo. Restrições UNIQUE, CHECK e regras de cobertura estão no dicionário do banco. As setas não representam fluxo de dados.</p>';}
for(const name of Object.keys(data.entities).sort()){$('tables').insertAdjacentHTML('beforeend','<option value="'+escape(name)+'">')}document.querySelectorAll('.entity').forEach(e=>{e.onclick=()=>select(e.dataset.name);e.onkeydown=event=>{if(event.key==='Enter')select(e.dataset.name)}});$('search').onchange=()=>{const name=$('search').value;select(name);const e=document.querySelector('[data-name="'+CSS.escape(name)+'"]');if(e)e.scrollIntoView({block:'center',inline:'center',behavior:'smooth'})};$('reset').onclick=()=>{document.querySelectorAll('.dim,.active-edge').forEach(e=>e.classList.remove('dim','active-edge'));$('search').value='';$('name').textContent='Selecione uma tabela';$('description').textContent='34 tabelas agrupadas por domínio. Clique para explorar.';$('details').innerHTML=''};</script></html>'''
    page = template.replace('__SVG__',svg).replace('__DATA__',json.dumps({'entities':entities,'relations':relations},ensure_ascii=False).replace('</','<\\/'))
    (ROOT/'UML_BANCO.html').write_text(page)
    print(f'Geradas {len(entities)} tabelas e {len(relations)} FKs em {ROOT}')


if __name__ == '__main__':
    main()
