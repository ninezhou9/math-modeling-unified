import argparse
import json
import os
from pathlib import Path


def convert(pdf_path, output_dir, max_dim=1000):
    source = Path(pdf_path).resolve()
    output = Path(output_dir).resolve()
    if not source.is_file() or source.suffix.casefold() != ".pdf":
        raise ValueError(f"input PDF does not exist or is not a .pdf file: {source}")
    if isinstance(max_dim, bool) or not isinstance(max_dim, int) or max_dim <= 0:
        raise ValueError("--max-dim must be a positive integer")

    from pdf2image import convert_from_path

    images = convert_from_path(source, dpi=200)
    output.mkdir(parents=True, exist_ok=True)

    for i, image in enumerate(images):
        width, height = image.size
        if width > max_dim or height > max_dim:
            scale_factor = min(max_dim / width, max_dim / height)
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            image = image.resize((new_width, new_height))
        
        image_path = os.path.join(output, f"page_{i+1}.png")
        image.save(image_path)

    return {
        "status": "success",
        "pages": len(images),
        "output_directory": str(output),
    }


def friendly_error(error: Exception) -> str:
    name = type(error).__name__
    if isinstance(error, ModuleNotFoundError) and (
        getattr(error, "name", None) == "pdf2image" or "pdf2image" in str(error)
    ):
        return "Missing Python dependency: run `pip install pdf2image`."
    if "PDFInfoNotInstalledError" in name:
        return "Poppler is unavailable; install Poppler and ensure pdftoppm/pdfinfo is on PATH."
    if name in {"PDFPageCountError", "PDFSyntaxError"}:
        return f"PDF rendering failed; verify the input PDF and Poppler installation: {error}"
    return str(error) or name


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert each page of an input PDF to a size-bounded PNG preview."
    )
    parser.add_argument("input_pdf", help="Input PDF file")
    parser.add_argument("output_directory", help="Output directory for page_N.png files")
    parser.add_argument(
        "--max-dim",
        type=int,
        default=1000,
        help="Maximum PNG width or height in pixels (default: 1000)",
    )
    args = parser.parse_args()
    try:
        result = convert(args.input_pdf, args.output_directory, max_dim=args.max_dim)
    except Exception as error:
        print(json.dumps({"status": "error", "error": friendly_error(error)}))
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
