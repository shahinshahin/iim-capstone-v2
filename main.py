from fastapi import FastAPI, File, UploadFile, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import shutil
import os

from vector_store import embed_and_store, query_index, compute_material_cost

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

UPLOAD_DIR = "temp_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    temp_file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(temp_file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    msg = embed_and_store(temp_file_path)
    return RedirectResponse("/", status_code=303)


@app.post("/query", response_class=HTMLResponse)
async def run_query(request: Request, query: str = Form(...)):
    result = query_index(query)
    return templates.TemplateResponse("index.html", {"request": request, "result": result})

@app.post("/query/cost", response_class=HTMLResponse)
async def query_with_cost(request: Request, query: str = Form(...)):
    extracted = query_index(query)

    # Handle different formats from Pinecone metadata
    raw_materials = extracted.get("Raw Materials", [])
    quantities = extracted.get("Sub QTY", [])
    
    if isinstance(raw_materials, str):
        raw_materials = [raw_materials]
    if isinstance(quantities, (int, float, str)):
        quantities = [quantities]

    # Ensure both lists are aligned
    materials = []
    for i in range(len(raw_materials)):
        materials.append({
            "Raw Materials": raw_materials[i],
            "Sub QTY": quantities[i] if i < len(quantities) else 1,
            "Original": extracted.get("Original", "")  # For fuzzy match fallback
        })

    cost_result = compute_material_cost(materials)

    return templates.TemplateResponse("index.html", {
        "request": request,
        "cost_result": cost_result,
        "result": extracted
    })

@app.get("/download-cost-summary")
async def download_cost_summary():
    file_path = "outputs/material_cost_summary.xlsx"
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', filename="material_cost_summary.xlsx")
    return {"error": "No summary available yet."}