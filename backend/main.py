# -*- coding: utf-8 -*-
"""
FastAPI Backend для FSM Graph Visualizer
Использует существующие функции из FSM_Graph_Viz без изменений
"""

import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

# Добавляем путь к модулям FSM_Graph_Viz
fsm_viz_path = Path(__file__).parent.parent / "FSM_Graph_Viz"
sys.path.insert(0, str(fsm_viz_path))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from cst_service import CSTService
from fsm_graph_builder import build_fsm_graphs_from_cst
from fsm_graph_viz import fsm_graph_to_html, fsm_graph_to_svg
from code_generator import FSMCodeGenerator

app = FastAPI(title="FSM Graph Visualizer API", version="1.0.0")

# CORS для работы с React фронтендом
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Хранилище графов в памяти (в продакшене использовать БД)
graphs_storage: List[Dict[str, Any]] = []
current_parse_id: int = 0
original_code_storage: Dict[int, str] = {}  # Хранилище исходного кода по parse_id


class ParseRequest(BaseModel):
    code: str
    filename: Optional[str] = "source.sv"


class ParseResponse(BaseModel):
    success: bool
    graphs_count: int
    graphs: List[Dict[str, Any]]
    parse_id: int


@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {
        "message": "FSM Graph Visualizer API",
        "version": "1.0.0",
        "endpoints": {
            "POST /api/parse": "Парсинг SystemVerilog кода",
            "GET /api/graphs": "Получить все графы",
            "GET /api/graph/{id}": "Получить конкретный граф",
            "GET /api/export/{id}/html": "Экспорт графа в HTML",
            "GET /api/export/{id}/svg": "Экспорт графа в SVG",
        }
    }


@app.post("/api/parse", response_model=ParseResponse)
async def parse_code(request: ParseRequest):
    """
    Парсинг SystemVerilog кода и построение FSM-графов.
    Использует существующие функции без изменений.
    """
    try:
        # Используем существующий CSTService
        cst_service = CSTService()
        tree = cst_service.build_cst_from_text(
            request.code,
            request.filename or "source.sv"
        )
        
        # Используем существующую функцию построения графов
        graphs = build_fsm_graphs_from_cst(tree)
        
        # Сохраняем графы в хранилище
        global current_parse_id, graphs_storage, original_code_storage
        current_parse_id += 1
        parse_id = current_parse_id
        
        # Сохраняем исходный код
        original_code_storage[parse_id] = request.code
        
        # Добавляем parse_id к каждому графу для идентификации
        for i, graph in enumerate(graphs):
            graph["parse_id"] = parse_id
            graph["graph_id"] = f"{parse_id}_{i}"
        
        graphs_storage = graphs
        
        return ParseResponse(
            success=True,
            graphs_count=len(graphs),
            graphs=graphs,
            parse_id=parse_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка парсинга: {str(e)}")


@app.get("/api/graphs")
async def get_all_graphs():
    """Получить все графы из последнего парсинга"""
    return {
        "graphs": graphs_storage,
        "count": len(graphs_storage)
    }


@app.get("/api/graph/{graph_id}")
async def get_graph(graph_id: str):
    """Получить конкретный граф по ID"""
    graph = next((g for g in graphs_storage if g.get("graph_id") == graph_id), None)
    if graph is None:
        raise HTTPException(status_code=404, detail="Граф не найден")
    return graph


@app.get("/api/export/{graph_id}/html")
async def export_html(graph_id: str, width: int = 900, height: int = 650):
    """Экспорт графа в HTML (использует существующую функцию)"""
    graph = next((g for g in graphs_storage if g.get("graph_id") == graph_id), None)
    if graph is None:
        raise HTTPException(status_code=404, detail="Граф не найден")
    
    try:
        scope = graph.get("scope", "fsm")
        title = f"FSM Graph - {scope}"
        html = fsm_graph_to_html(graph, title=title, width=width, height=height)
        return {"html": html}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка экспорта: {str(e)}")


@app.get("/api/export/{graph_id}/svg")
async def export_svg(graph_id: str, width: int = 800, height: int = 600):
    """Экспорт графа в SVG (использует существующую функцию)"""
    graph = next((g for g in graphs_storage if g.get("graph_id") == graph_id), None)
    if graph is None:
        raise HTTPException(status_code=404, detail="Граф не найден")
    
    try:
        svg = fsm_graph_to_svg(graph, width=width, height=height)
        return {"svg": svg}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка экспорта: {str(e)}")


class UpdateGraphRequest(BaseModel):
    graph: Dict[str, Any]


@app.post("/api/graph/{graph_id}/update")
async def update_graph(graph_id: str, request: UpdateGraphRequest):
    """Обновить граф (для интерактивного редактирования)"""
    graph_index = next(
        (i for i, g in enumerate(graphs_storage) if g.get("graph_id") == graph_id),
        None
    )
    if graph_index is None:
        raise HTTPException(status_code=404, detail="Граф не найден")
    
    try:
        # Обновляем граф
        updated_graph = request.graph
        updated_graph["graph_id"] = graph_id
        updated_graph["parse_id"] = graphs_storage[graph_index].get("parse_id")
        
        graphs_storage[graph_index] = updated_graph
        
        return {"success": True, "graph": updated_graph}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка обновления: {str(e)}")


@app.post("/api/graph/{graph_id}/generate-code")
async def generate_code(graph_id: str):
    """Генерировать SystemVerilog код из отредактированного графа"""
    graph = next((g for g in graphs_storage if g.get("graph_id") == graph_id), None)
    if graph is None:
        raise HTTPException(status_code=404, detail="Граф не найден")
    
    try:
        parse_id = graph.get("parse_id")
        original_code = original_code_storage.get(parse_id, "")
        
        generator = FSMCodeGenerator(original_code)
        
        scope = graph.get("scope", "module fsm_example")
        parts = scope.split()
        module_name = parts[-1] if len(parts) > 1 else "fsm_example"
        
        generated_code = generator.generate_code_from_graph(graph, module_name)
        
        return {"code": generated_code}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка генерации кода: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

