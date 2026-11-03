"""Merge PDF files inside Pyodide's virtual file system.

index.html writes the selected PDFs into INPUT_DIR via
``pyodide.FS.writeFile()`` and then executes this file with
``pyodide.runPython()`` / ``runPythonAsync()``.  The merged result is
written to OUTPUT_PATH, where index.html reads it back with
``pyodide.FS.readFile()`` and offers it as a download.

The script also runs standalone (e.g. in the project .venv) for local
testing: point PDF_MERGER_INPUT_DIR / PDF_MERGER_OUTPUT_PATH at real
directories, e.g.

    PDF_MERGER_INPUT_DIR=/tmp/pdfin \
    PDF_MERGER_OUTPUT_PATH=/tmp/pdfout/merged.pdf \
    .venv/bin/python src/main.py
"""

import os
import sys

INPUT_DIR = os.environ.get("PDF_MERGER_INPUT_DIR", "/home/pyodide/inputs")
OUTPUT_PATH = os.environ.get(
    "PDF_MERGER_OUTPUT_PATH", "/home/pyodide/output/merged.pdf"
)


def log(msg: str) -> None:
    """Send a progress message to the browser UI.

    In the browser ``js_log`` is a JavaScript function injected by
    index.html via ``pyodide.globals.set("js_log", fn)`` (JS -> Python
    passthrough).  Outside Pyodide we fall back to print().
    """
    js_fn = globals().get("js_log")
    if callable(js_fn):
        js_fn(str(msg))
    else:
        print(msg, flush=True)


def merge_pdfs() -> str:
    from pypdf import PdfReader, PdfWriter

    names = sorted(n for n in os.listdir(INPUT_DIR) if n.lower().endswith(".pdf"))
    if len(names) < 2:
        raise ValueError(
            f"Need at least 2 PDFs to merge, found {len(names)} in {INPUT_DIR}"
        )

    log(f"Merging {len(names)} PDFs from {INPUT_DIR} ...")
    writer = PdfWriter()
    for name in names:
        path = os.path.join(INPUT_DIR, name)
        reader = PdfReader(path)
        if reader.is_encrypted:
            # Try the empty password; most "encrypted" PDFs open with it.
            if not reader.decrypt(""):
                raise PermissionError(f"{name} is encrypted and could not be opened")
        n_pages = len(reader.pages)
        for page in reader.pages:
            writer.add_page(page)
        log(f"  + {n_pages} page(s) from {name}")

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "wb") as fh:
        writer.write(fh)

    size = os.path.getsize(OUTPUT_PATH)
    log(f"Wrote {OUTPUT_PATH}: {len(writer.pages)} pages, {size:,} bytes")
    return OUTPUT_PATH


if __name__ == "__main__" and sys.platform != "emscripten":
    # Auto-run only for local CLI testing; in the browser index.html calls
    # merge_pdfs() explicitly (sys.platform is "emscripten" under Pyodide).
    merge_pdfs()
