import io
import pandas as pd

def read_file(filename, content_bytes):
    ext = filename.lower().split('.')[-1]
    if ext == 'csv':
        df = pd.read_csv(io.BytesIO(content_bytes))
    elif ext in ['xls', 'xlsx']:
        df = pd.read_excel(io.BytesIO(content_bytes))
    else:
        raise ValueError("Unsupported file format")
    return df.astype(str).apply(lambda x: ' '.join(x), axis=1).tolist()