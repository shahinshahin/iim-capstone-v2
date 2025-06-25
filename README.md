# 🧠 Capstone Vector Search App

This is a full-stack application that allows users to:
- Upload `.csv` or `.xlsx` files containing text data
- Store their embeddings in a Pinecone vector index
- Query the index using natural language and retrieve the most relevant matches

Built using **FastAPI**, **Sentence Transformers**, **Pinecone**, and **HTML (Jinja2)**.

---

## 🚀 Features

- ✅ Upload `.csv` / `.xlsx` files with text data
- ✅ Generate semantic embeddings using `sentence-transformers`
- ✅ Store embeddings in Pinecone vector DB
- ✅ Search using natural language queries
- ✅ Simple, clean frontend interface

---

## 🏗️ Tech Stack

| Layer       | Technology               |
|-------------|---------------------------|
| Backend     | [FastAPI](https://fastapi.tiangolo.com) |
| Embeddings  | [Sentence Transformers](https://www.sbert.net/) |
| Vector DB   | [Pinecone](https://www.pinecone.io) |
| Frontend    | HTML (Jinja2 Templates) |
| Server      | [Uvicorn](https://www.uvicorn.org/) |

---

## 📁 Project Structure

```
iim-capstone-v2/
├── main.py                # FastAPI app
├── vector_store.py        # Pinecone + embeddings logic
├── templates/
│   └── index.html         # Web UI
├── static/                # CSS/JS files (optional)
├── temp_files/            # Temporary upload storage
├── .env                   # API keys (not committed)
├── requirements.txt       # Python dependencies
└── README.md              # You're here!
```

---

## ⚙️ Setup Instructions

### 1. Clone the Repo

```bash
git clone https://github.com/YOUR_USERNAME/iim-capstone-v2.git
cd iim-capstone-v2
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Requirements

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the root:

```env
PINECONE_API_KEY=your_api_key_here
PINECONE_INDEX_NAME=your_index_name
```

Make sure your Pinecone index is created with the correct vector dimension (e.g., 384 for `all-MiniLM-L6-v2`).

### 5. Run the App

```bash
uvicorn main:app --reload
```

Go to `http://127.0.0.1:8000`

---

## 📝 Supported File Formats

| Format    | Description           |
|-----------|-----------------------|
| `.csv`    | Any CSV with rows of text |
| `.xlsx`   | Excel files (text rows) |

---

## 🧪 Example Usage

1. Upload a file like:

```csv
text
The capital of India is New Delhi.
The Earth revolves around the Sun.
```

2. Enter a query like:

> "What is the capital of India?"

3. See the most semantically relevant match from the uploaded content.

---

## 🔒 Note

Ensure your `.env` file is never committed to Git. It's already in `.gitignore`.

---

## 📜 License

This project is for educational/demonstration purposes. Use it as a base for your own vector-based search applications.

---

## 🙌 Contributions Welcome

Feel free to fork, improve, or suggest changes via issues or pull requests.