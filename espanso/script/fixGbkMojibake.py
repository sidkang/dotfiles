import sys
import unicodedata


def main() -> None:
    text = sys.argv[1] if len(sys.argv) > 1 else ""
    normalized = unicodedata.normalize("NFC", text)
    try:
        sys.stdout.write(normalized.encode("latin1").decode("gbk"))
    except UnicodeError:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
