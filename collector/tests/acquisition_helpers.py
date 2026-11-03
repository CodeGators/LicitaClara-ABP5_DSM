import io
from zipfile import ZipFile


def zip_bytes(content=b"id;nome\n1;Teste\n", name="dados.csv"):
    result = io.BytesIO()
    with ZipFile(result, "w") as archive:
        archive.writestr(name, content)
    return result.getvalue()
