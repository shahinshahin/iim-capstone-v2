from fastapi import FastAPI, File, UploadFile, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import shutil
from vector_store import embed_and_store, query_index  # your functions

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    temp_file_path = f"temp_files/{file.filename}"
    with open(temp_file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    embed_and_store(temp_file_path)
    return RedirectResponse("/", status_code=303)


@app.post("/query", response_class=HTMLResponse)
async def run_query(request: Request, query: str = Form(...)):
    result = query_index(query)
    return templates.TemplateResponse("index.html", {"request": request, "result": result})
