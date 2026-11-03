from dataclasses import dataclass
from datetime import date
from html.parser import HTMLParser
from http.client import HTTPException
from urllib.parse import urljoin

from licita_collector.errors import TransientFailure, Unavailable

BASE_URL = "https://repositorio.dados.gov.br/seges/comprasgov/"
FILES = {
    "compra": "pncp",
    "compra_item": "pncp",
    "item_resultado": "pncp",
    "material": "pesquisa_precos",
    "propostas": "propostas",
}


def month(value: str) -> date:
    if len(value) != 7:
        raise ValueError("Competência deve ser YYYY-MM")
    return date.fromisoformat(value + "-01")


def months(start: date, end: date):
    if start > end:
        raise ValueError("Intervalo inicial posterior ao final")
    current = start
    while current <= end:
        yield current
        current = date(current.year + (current.month == 12), current.month % 12 + 1, 1)


@dataclass(frozen=True)
class Scope:
    kind: str
    competence: date

    def __post_init__(self):
        if self.kind not in FILES or self.competence.day != 1:
            raise ValueError("Arquivo/competência inválido")

    @property
    def source(self):
        return "comprasgov"

    @property
    def parameters(self):
        return {
            "arquivo": self.filename,
            "competencia_semantica": {
                "material": "data_compra",
                "propostas": "inclusao_item_seguindo_LEIAME",
            }.get(self.kind, "data_publicacao_pncp"),
        }

    @property
    def module(self):
        return f"{FILES[self.kind]}/{self.kind}"

    @property
    def filename(self):
        if self.kind == "propostas":
            return f"propostas-{self.competence:%Y-%m}.csv.zip"
        return f"{self.kind}_{self.competence:%Y_%m}.csv.zip"

    def directory(self, base=BASE_URL):
        return f"{base}{FILES[self.kind]}/{self.competence:%Y/%m}/"


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = set()

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.links.update(value for name, value in attrs if name == "href" and value)


def discover(scope: Scope, http, base=BASE_URL):
    directory = scope.directory(base)
    for attempt in range(http.settings.collector_attempts):
        try:
            with http.request(directory, attempts=1) as response:
                body = response.read(1024 * 1024 + 1)
                if len(body) > 1024 * 1024:
                    raise Unavailable("Índice da competência excede limite")
                parser = Links()
                parser.feed(body.decode("utf-8"))
            break
        except (OSError, HTTPException, TransientFailure):
            if attempt + 1 == http.settings.collector_attempts:
                raise TransientFailure("Falha ao ler o índice da competência") from None
            http.sleep(min(2**attempt, 4))
    expected = directory + scope.filename
    if not any(urljoin(directory, link) == expected for link in parser.links):
        raise Unavailable("Arquivo não anunciado no índice oficial da competência")
    return expected
