# FSM_Graph_Viz

Проект для анализа SystemVerilog кода с автоматическим детектированием и визуализацией конечных автоматов (Finite State Machines, FSM).

## Описание

**FSM_Graph_Viz** - это комплексная система для анализа SystemVerilog кода, которая:
- Парсит SystemVerilog код в Concrete Syntax Tree (CST) с использованием библиотеки `pyslang`
- Строит Abstract Syntax Tree (AST) из CST
- Автоматически детектирует FSM в модулях SystemVerilog
- Извлекает состояния, переходы и метаданные FSM
- Строит графы переходов FSM
- Визуализирует FSM через GUI (Tkinter) и экспортирует в HTML/SVG

## Структура проекта

```
FSM_Graph_Viz/
├── AST_CST/                    # Пакет для работы с CST и AST
│   ├── __init__.py            # Экспорт публичных API
│   ├── cst_service.py         # Базовый сервис для работы с CST
│   └── ast_service.py         # Базовый AST сервис
├── FSM_core/                   # Пакет для детектирования и визуализации FSM
│   ├── __init__.py            # Экспорт публичных API
│   ├── FindeENUM.py           # Детектор enum переменных
│   ├── fsm_enum_candidates_cst.py  # Фильтрация enum кандидатов
│   ├── fsm_graph_builder.py   # Построение графов FSM
│   └── fsm_graph_viz.py       # GUI визуализатор FSM
├── tests/                      # Тестовые файлы
│   ├── test_free.py           # CompleteASTService (полный AST сервис)
│   ├── test_fsm_graph_builder.py  # Тесты для fsm_graph_builder
│   └── TESTENUM.py            # Тест для enum детектора
└── project_analysis_report/    # Документация проекта
    └── ПОЛНЫЙ_ОТЧЕТ_ПО_ПРОЕКТУ.md
```

## Требования

- Python 3.x
- pyslang - библиотека для парсинга SystemVerilog
- tkinter - GUI фреймворк (обычно входит в стандартную поставку Python)

## Установка

```bash
# Клонировать репозиторий
git clone https://github.com/Aushota1/FSM_Graph_Viz.git
cd FSM_Graph_Viz

# Установить зависимости
pip install pyslang
```

## Использование

### GUI приложение

Запуск графического интерфейса для визуализации FSM:

```bash
python -m FSM_core.fsm_graph_viz
```

### Программное использование

```python
from AST_CST.cst_service import build_cst_from_text
from FSM_core.fsm_graph_builder import build_fsm_graphs_from_cst

# Загрузить SystemVerilog код
with open('example.sv', 'r') as f:
    sv_code = f.read()

# Построить CST
tree = build_cst_from_text(sv_code, 'example.sv')

# Построить графы FSM
fsm_graphs = build_fsm_graphs_from_cst(tree)

# Работать с графами FSM
for graph in fsm_graphs:
    print(f"FSM в scope: {graph['scope']}")
    print(f"Состояния: {graph['states']}")
    print(f"Переходы: {graph['transitions']}")
```

## Тестирование

```bash
# Запустить тесты
python -m pytest tests/

# Или отдельные тесты
python tests/test_fsm_graph_builder.py
python tests/TESTENUM.py
```

## Документация

Подробная документация доступна в файле `project_analysis_report/ПОЛНЫЙ_ОТЧЕТ_ПО_ПРОЕКТУ.md`

## Лицензия

[Указать лицензию]

## Авторы

[Указать авторов]

## Ссылки

- Репозиторий: https://github.com/Aushota1/FSM_Graph_Viz.git

