"""Executa o notebook isolado e exporta uma cópia HTML sem acessar o banco."""

import sys
from pathlib import Path

import nbformat
from jupyter_client import KernelManager
from nbclient import NotebookClient
from nbconvert import HTMLExporter


def main():
    folder = Path(__file__).resolve().parent
    root = folder.parents[1]
    path = folder / "analise_if_teclado.ipynb"
    notebook = nbformat.read(path, as_version=4)
    manager = KernelManager(kernel_name="python3")
    manager.kernel_spec.argv = [
        sys.executable,
        "-m",
        "ipykernel_launcher",
        "-f",
        "{connection_file}",
    ]
    print("Executando todas as células, com conferência dos ZIPs originais...", flush=True)
    client = NotebookClient(
        notebook, km=manager, timeout=240, resources={"metadata": {"path": str(root)}}
    )
    client.execute()
    nbformat.validate(notebook)
    nbformat.write(notebook, path)
    body, _ = HTMLExporter().from_notebook_node(notebook)
    (folder / "analise_if_teclado.html").write_text(body)
    print("Concluído: notebook executado e HTML salvos em", folder)
    print("Tabelas, gráficos e conclusão em", root / "data/experimentos/if_teclado")


if __name__ == "__main__":
    main()
