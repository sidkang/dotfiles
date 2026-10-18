import base64
import os
import sys

content = os.environ.get("ESPANSO_FORM_CONTENT", "")

sys.stdout.write(base64.b64encode(content.encode("utf-8")).decode("ascii"))
