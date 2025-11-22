# -*- coding: utf-8 -*-
# sv_analyzer_testbench.py
"""
Большой тестовый стенд для:
  - sv_analyzer/analyze_systemverilog_code (CompleteAST + отчётность)
  - FSMDetectorService.detect_finite_state_machines

Сценарий:
  1. Для каждого тестового SystemVerilog-модуля:
     - строим CST (CSTService)
     - строим полный AST (analyze_systemverilog_code → CompleteASTService внутри)
     - достаём нужный модуль из AST
     - запускаем FSMDetectorService
  2. Собираем:
     - бинарную метку: есть FSM или нет (has_fsm_true vs detected_pred)
     - регрессию: "истинное" число состояний vs число состояний, найденных детектором
  3. Рассчитываем MAE, MSE, RMSE, R² для числа состояний.
  4. Рассчитываем accuracy/precision/recall/F1 для бинарного детекта FSM.
  5. Печатаем подробный отчёт по каждому тесту + агрегированные метрики.

Предполагается, что рядом лежат:
  - cst_service.py
  - sv_analyzer.py
  - fsm_detector_service.py
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from cst_service import CSTService
from sv_analyzer import analyze_systemverilog_code
from fsm_detector_service import FSMDetectorService


# -----------------------------------------------------------------------------
# Модель тест-кейса
# -----------------------------------------------------------------------------

@dataclass
class FSMTestCase:
    id: str
    description: str
    module_name: str
    sv_code: str
    # ожидаемая "истина"
    expect_has_fsm: bool
    expect_num_states: int


# -----------------------------------------------------------------------------
# Набор тестов (SystemVerilog-код)
# -----------------------------------------------------------------------------
# Важно: каждый тест — независимый небольшой модуль.
# Ты можешь расширять/править этот список, это просто стартовый "большой" пакет.
# -----------------------------------------------------------------------------

TEST_CASES: List[FSMTestCase] = [

    # 1. Простой enum FSM (классика)
    FSMTestCase(
        id="enum_simple",
        description="Простой FSM на enum logic, классический пример",
        module_name="fsm_example1_enum_simple",
        sv_code=r"""
module fsm_example1_enum_simple (
    input  logic clk,
    input  logic rst,
    input  logic start,
    output logic done
);
    typedef enum logic [1:0] {
        IDLE = 2'b00,
        RUN  = 2'b01,
        DONE = 2'b10
    } state_t;

    state_t state, next_state;

    // регистр состояния
    always_ff @(posedge clk or posedge rst) begin
        if (rst)
            state <= IDLE;
        else
            state <= next_state;
    end

    // переходы
    always_comb begin
        next_state = state;
        case (state)
            IDLE: if (start) next_state = RUN;
            RUN:  next_state = DONE;
            DONE: next_state = IDLE;
        endcase
    end

    // выход
    assign done = (state == DONE);

endmodule
""",
        expect_has_fsm=True,
        expect_num_states=3,
    ),

    # 2. FSM на параметрах (IDLE/RUN/STOP как localparam)
    FSMTestCase(
        id="params_based_fsm",
        description="FSM через localparam, без typedef enum",
        module_name="fsm_example2_params",
        sv_code=r"""
module fsm_example2_params (
    input  wire clk,
    input  wire rst,
    input  wire start,
    output reg  run_led
);
    localparam IDLE = 2'b00;
    localparam RUN  = 2'b01;
    localparam STOP = 2'b10;

    reg [1:0] current_state, next_state;

    always @(posedge clk or posedge rst) begin
        if (rst)
            current_state <= IDLE;
        else
            current_state <= next_state;
    end

    always @* begin
        next_state = current_state;
        case (current_state)
            IDLE: if (start) next_state = RUN;
            RUN:  next_state = STOP;
            STOP: next_state = IDLE;
            default: next_state = IDLE;
        endcase
    end

    always @* begin
        run_led = (current_state == RUN);
    end
endmodule
""",
        expect_has_fsm=True,
        expect_num_states=3,
    ),

    # 3. FSM с "plain" именами сигналов (state_reg/state_next)
    FSMTestCase(
        id="plain_names",
        description="FSM с именами state_reg/state_next без enum/params",
        module_name="fsm_example3_plain_names",
        sv_code=r"""
module fsm_example3_plain_names (
    input  logic clk,
    input  logic rst,
    input  logic x,
    output logic y
);
    logic [1:0] state_reg, state_next;

    always_ff @(posedge clk or posedge rst) begin
        if (rst)
            state_reg <= 2'b00;
        else
            state_reg <= state_next;
    end

    always_comb begin
        state_next = state_reg;
        case (state_reg)
            2'b00: if (x) state_next = 2'b01;
            2'b01: state_next = 2'b10;
            2'b10: state_next = 2'b00;
            default: state_next = 2'b00;
        endcase
    end

    assign y = (state_reg == 2'b10);

endmodule
""",
        expect_has_fsm=True,
        # "Истинное" число состояний 3, но детектор может не вытащить имена, поэтому
        # мы здесь задаём ground truth = 3 (будем смотреть MSE).
        expect_num_states=3,
    ),

    # 4. Модуль без FSM (простой счётчик)
    FSMTestCase(
        id="no_fsm_counter",
        description="Простой счётчик, не FSM",
        module_name="simple_counter",
        sv_code=r"""
module simple_counter (
    input  wire clk,
    input  wire rst,
    output reg  [7:0] count
);
    always @(posedge clk or posedge rst) begin
        if (rst)
            count <= 8'd0;
        else
            count <= count + 1'b1;
    end
endmodule
""",
        expect_has_fsm=False,
        expect_num_states=0,
    ),

    # 5. FSM "control" с сигналами current_state/next_state (твоего стиля)
    FSMTestCase(
        id="ctrl_style",
        description="FSM c current_state/next_state (стиль control)",
        module_name="fsm_example5_ctrl",
        sv_code=r"""
module fsm_example5_ctrl (
    input  wire clk,
    input  wire rst,
    input  wire go,
    output reg  busy
);
    localparam IDLE  = 2'b00;
    localparam LOAD  = 2'b01;
    localparam WORK  = 2'b10;
    localparam DONE  = 2'b11;

    reg [1:0] current_state, next_state;

    always @(posedge clk or posedge rst) begin
        if (rst)
            current_state <= IDLE;
        else
            current_state <= next_state;
    end

    always @* begin
        next_state = current_state;
        case (current_state)
            IDLE:  if (go) next_state = LOAD;
            LOAD:  next_state = WORK;
            WORK:  next_state = DONE;
            DONE:  next_state = IDLE;
            default: next_state = IDLE;
        endcase
    end

    always @* begin
        busy = (current_state == WORK);
    end

endmodule
""",
        expect_has_fsm=True,
        expect_num_states=4,
    ),

    # 6. "Счётчик-состояние" (fake FSM) — он может считаться FSM по эвристике
    FSMTestCase(
        id="fake_state_counter",
        description="state_counter — по сути счётчик, но имя содержит 'state'",
        module_name="fsm_example8_fake_state",
        sv_code=r"""
module fsm_example8_fake_state (
    input  wire clk,
    input  wire rst,
    output reg  [7:0] out
);
    reg [7:0] state_counter;

    always @(posedge clk or posedge rst) begin
        if (rst)
            state_counter <= 8'd0;
        else
            state_counter <= state_counter + 8'd1;
    end

    assign out = state_counter;
endmodule
""",
        # "Истинно" FSM здесь, скорее всего, НЕТ, но детектор по имени "state_counter"
        # может его считать. Для оценки качества задаём ground truth=False.
        expect_has_fsm=False,
        expect_num_states=0,
    ),

    # 7. Твой классический пример detect_4_bit_sequence_using_fsm
    FSMTestCase(
        id="ticket_1010",
        description="FSM детектора последовательности 1010 (enum logic [2:0])",
        module_name="detect_4_bit_sequence_using_fsm",
        sv_code=r"""
module detect_4_bit_sequence_using_fsm
(
  input  clk,
  input  rst,
  input  a,
  output detected
);

  // Detection of the "1010" sequence

  // States (F — First, S — Second)
  enum logic[2:0]
  {
     IDLE   = 3'b001,
     F1     = 3'b000,
     F0     = 3'b010,
     S1     = 3'b011,
     S0     = 3'b100
  }
  state, new_state;

  // State transition logic
  always_comb
  begin
    new_state = state;

    case (state)
      IDLE: if (  a) new_state = F1;
      F1:   if (~ a) new_state = F0;
      F0:   if (  a) new_state = S1;
            else     new_state = IDLE;
      S1:   if (~ a) new_state = S0;
            else     new_state = F1;
      S0:   if (  a) new_state = S1;
            else     new_state = IDLE;
    endcase
  end

  // Output logic (depends only on the current state)
  assign detected = (state == S0);

  // State update
  always_ff @ (posedge clk)
    if (rst)
      state <= IDLE;
    else
      state <= new_state;

endmodule
""",
        expect_has_fsm=True,
        expect_num_states=5,  # IDLE, F1, F0, S1, S0
    ),
]


# -----------------------------------------------------------------------------
# Метрики: MAE, MSE, RMSE, R2
# -----------------------------------------------------------------------------

def compute_regression_metrics(y_true: List[float], y_pred: List[float]) -> Dict[str, float]:
    """
    Рассчёт MAE, MSE, RMSE, R² (без sklearn).
    """
    n = len(y_true)
    if n == 0:
        return {"MAE": 0.0, "MSE": 0.0, "RMSE": 0.0, "R2": 0.0}

    # MAE
    abs_errors = [abs(t - p) for t, p in zip(y_true, y_pred)]
    mae = sum(abs_errors) / n

    # MSE
    sq_errors = [(t - p) ** 2 for t, p in zip(y_true, y_pred)]
    mse = sum(sq_errors) / n

    # RMSE
    rmse = mse ** 0.5

    # R²
    mean_true = sum(y_true) / n
    ss_tot = sum((t - mean_true) ** 2 for t in y_true)
    ss_res = sum((t - p) ** 2 for t, p in zip(y_true, y_pred))
    if ss_tot > 0:
        r2 = 1.0 - ss_res / ss_tot
    else:
        # если нет разброса в y_true, R² не очень осмыслен, но вернём 1.0 при идеальном предсказании
        r2 = 1.0 if ss_res == 0 else 0.0

    return {"MAE": mae, "MSE": mse, "RMSE": rmse, "R2": r2}


def compute_classification_metrics(y_true: List[int], y_pred: List[int]) -> Dict[str, float]:
    """
    Простые метрики бинарной классификации: accuracy, precision, recall, F1.
    y_true / y_pred ∈ {0, 1}.
    """
    assert len(y_true) == len(y_pred)
    n = len(y_true)
    if n == 0:
        return {"accuracy": 0.0, "precision": 0.0, "recall": 0.0, "f1": 0.0}

    tp = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 1)
    tn = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 0)
    fp = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 1)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 0)

    accuracy = (tp + tn) / n
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    if precision + recall > 0:
        f1 = 2 * precision * recall / (precision + recall)
    else:
        f1 = 0.0

    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


# -----------------------------------------------------------------------------
# Запуск одного теста
# -----------------------------------------------------------------------------

def run_single_test(case: FSMTestCase) -> Dict[str, Any]:
    """
    Запускает полный пайплайн для одного теста:
      - CST
      - полный AST (CompleteAST)
      - FSMDetectorService для указанного модуля
    Возвращает dict с фактическими значениями:
      {
        "has_fsm_true": int,
        "has_fsm_pred": int,
        "num_states_true": int,
        "num_states_pred": int,
        "fsm_info": {...}
      }
    """
    source_text = case.sv_code
    filename = f"{case.id}.sv"

    # 1. CST
    cst_service = CSTService()
    tree = cst_service.build_cst_from_text(source_text, filename)

    # 2. Полный AST (sv_analyzer → CompleteAST внутри)
    ast = analyze_systemverilog_code(
        source_text=source_text,
        filename=filename,
        use_complete_ast=True,
    )

    modules = ast.get("modules", []) or []
    target_module = None
    for m in modules:
        if m.get("name") == case.module_name:
            target_module = m
            break
    if target_module is None and modules:
        # fallback — первый модуль
        target_module = modules[0]

    if target_module is None:
        raise RuntimeError(f"[{case.id}] Не удалось найти ни одного модуля в AST.")

    # 3. FSM детектор
    detector = FSMDetectorService()
    fsm_info = detector.detect_finite_state_machines(target_module, tree)

    has_fsm_pred = 1 if fsm_info.get("detected", False) else 0
    has_fsm_true = 1 if case.expect_has_fsm else 0

    num_states_pred = len(fsm_info.get("states", []) or [])
    num_states_true = case.expect_num_states

    return {
        "case": case,
        "has_fsm_true": has_fsm_true,
        "has_fsm_pred": has_fsm_pred,
        "num_states_true": num_states_true,
        "num_states_pred": num_states_pred,
        "fsm_info": fsm_info,
    }


# -----------------------------------------------------------------------------
# Запуск всех тестов + красивый отчёт и метрики
# -----------------------------------------------------------------------------

def run_all_tests() -> None:
    print("\n" + "=" * 80)
    print("SYSTEMVERILOG FSM ANALYZER — TEST BENCH")
    print("=" * 80 + "\n")

    y_true_fsm: List[int] = []
    y_pred_fsm: List[int] = []

    y_true_states: List[float] = []
    y_pred_states: List[float] = []

    all_results: List[Dict[str, Any]] = []

    # --- прогоняем все кейсы ---
    for case in TEST_CASES:
        print("-" * 80)
        print(f"Тест: {case.id}")
        print(f"Описание: {case.description}")
        print(f"Модуль: {case.module_name}")
        print("-" * 80)

        result = run_single_test(case)
        all_results.append(result)

        has_fsm_true = result["has_fsm_true"]
        has_fsm_pred = result["has_fsm_pred"]
        num_states_true = result["num_states_true"]
        num_states_pred = result["num_states_pred"]

        y_true_fsm.append(has_fsm_true)
        y_pred_fsm.append(has_fsm_pred)
        y_true_states.append(float(num_states_true))
        y_pred_states.append(float(num_states_pred))

        # Красивый вывод по тесту
        print(f"Ожидается FSM:       {bool(has_fsm_true)}")
        print(f"Обнаружен FSM:       {bool(has_fsm_pred)}")
        print(f"Истинное # состояний:{num_states_true}")
        print(f"Предсказанное # сост:{num_states_pred}")

        fsm_info = result["fsm_info"]
        if fsm_info.get("detected", False):
            print(f"  ➜ Тип FSM (детектор): {fsm_info.get('type', 'unknown')}")
            print(f"  ➜ Тактовый сигнал:    {fsm_info.get('clock_signal', 'unknown')}")
            print(f"  ➜ Условие сброса:     {fsm_info.get('reset_condition', 'unknown')}")
            states = fsm_info.get("states", []) or []
            if states:
                state_names = [st.get("name", "?") for st in states]
                print(f"  ➜ Найденные состояния ({len(states)}): {', '.join(state_names)}")
        else:
            print("  ➜ Детектор не нашёл FSM в этом модуле.")

        print()

    # --- агрегированные метрики ---

    print("\n" + "=" * 80)
    print("АГРЕГИРОВАННЫЕ МЕТРИКИ (FSM DETECTION)")
    print("=" * 80 + "\n")

    # Метрики классификации: обнаружен FSM / нет
    class_metrics = compute_classification_metrics(y_true_fsm, y_pred_fsm)
    print("Бинарная классификация: 'есть FSM' (True/False)")
    print(f"  Accuracy : {class_metrics['accuracy']:.3f}")
    print(f"  Precision: {class_metrics['precision']:.3f}")
    print(f"  Recall   : {class_metrics['recall']:.3f}")
    print(f"  F1-score : {class_metrics['f1']:.3f}")
    print()

    # Метрики регрессии: число состояний
    reg_metrics = compute_regression_metrics(y_true_states, y_pred_states)
    print("Регрессия: количество состояний (true vs predicted)")
    print(f"  MAE  : {reg_metrics['MAE']:.3f}")
    print(f"  MSE  : {reg_metrics['MSE']:.3f}")
    print(f"  RMSE : {reg_metrics['RMSE']:.3f}")
    print(f"  R²   : {reg_metrics['R2']:.3f}")
    print()

    # --- Табличка по каждому тесту ---

    print("\n" + "=" * 80)
    print("СВОДНАЯ ТАБЛИЦА ПО ТЕСТАМ")
    print("=" * 80 + "\n")

    header = f"{'ID':20} {'FSM_true':9} {'FSM_pred':9} {'#states_true':13} {'#states_pred':13}"
    print(header)
    print("-" * len(header))

    for r in all_results:
        case = r["case"]
        print(
            f"{case.id:20} "
            f"{bool(r['has_fsm_true']):9} "
            f"{bool(r['has_fsm_pred']):9} "
            f"{r['num_states_true']:13d} "
            f"{r['num_states_pred']:13d}"
        )

    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    run_all_tests()
