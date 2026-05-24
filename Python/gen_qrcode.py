import argparse
import qrcode


def gen_qrcode(url: str, img_out: str):
    """Generate a QR code image for a URL."""
    qrcode.make(url).save(img_out)
    print(f"QR code generated successfully at {img_out}!")


if __name__ == "__main__":
    # The formatter_class ensures line breaks in your epilog manual are preserved
    parser = argparse.ArgumentParser(
        description="QR CODE GENERATOR CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
USER MANUAL & EXAMPLES:
-----------------------
This utility converts any web link into a scannable QR code image.
Both the target URL and the output file name are strictly required.

Examples:
  python gen_qrcode.py https://example.com -o my_site.png
  python gen_qrcode.py https://google.com --output search_qr.jpg
        """,
    )

    # Removed default and nargs="?", making URL a required positional argument
    parser.add_argument(
        "url", help="The target web link/URL to encode into the QR code (Required)"
    )

    # Removed default=, added required=True to force user input for the output file
    parser.add_argument(
        "-o",
        "--output",
        required=True,
        help="The output filename for the image file, e.g., 'result.png' (Required)",
    )

    args = parser.parse_args()
    gen_qrcode(args.url, args.output)
