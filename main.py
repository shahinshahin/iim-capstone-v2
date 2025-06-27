from fastapi import FastAPI, File, UploadFile, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import shutil
import os

from vector_store import embed_and_store, query_index, compute_material_cost,get_all_pinecone_data

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

UPLOAD_DIR = "temp_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.get("/", response_class=HTMLResponse)
async def form_page(request: Request, message: str = ""):
    pinecone_data = get_all_pinecone_data()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "message": message,
        "pinecone_data": pinecone_data
    })

from fastapi.responses import JSONResponse

@app.get("/fetch-data")
async def fetch_pinecone_data():
    data = get_all_pinecone_data()
    return JSONResponse(content=data)


from fastapi.responses import RedirectResponse
from urllib.parse import urlencode

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    temp_file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(temp_file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    msg = embed_and_store(temp_file_path)
    query_params = urlencode({"message": "File uploaded and indexed successfully!"})
    return RedirectResponse(f"/?{query_params}", status_code=303)


@app.post("/query", response_class=HTMLResponse)
async def run_query(request: Request, query: str = Form(...)):
    result = query_index(query)
    return templates.TemplateResponse("index.html", {"request": request, "result": result})

@app.post("/query/cost", response_class=HTMLResponse)
async def query_with_cost(request: Request, query: str = Form(...)):
    extracted_list = query_index(query)  # now returns a list of dicts

    materials = []
    for item in extracted_list:
        raw_material = item.get("Raw Materials", "")
        sub_qty = item.get("Sub QTY", 1)
        original = item.get("Original", "")

        if isinstance(raw_material, str) and raw_material.strip():
            materials.append({
                "Raw Materials": raw_material,
                "Sub QTY": sub_qty,
                "Original": original
            })

    cost_result = compute_material_cost(materials)

    return templates.TemplateResponse("index.html", {
        "request": request,
        "cost_result": cost_result,
        "result": materials  # you can use this if needed in the HTML
    })

@app.get("/download-cost-summary")
async def download_cost_summary():
    file_path = "outputs/material_cost_summary.xlsx"
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', filename="material_cost_summary.xlsx")
    return {"error": "No summary available yet."}