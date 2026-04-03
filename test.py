import sys
import os
import traceback

sys.path.insert(0, os.path.abspath("."))
try:
    import api.server
    print('SUCCESS')
except Exception as e:
    with open("trace.txt", "w", encoding="utf-8") as f:
        f.write(traceback.format_exc())
