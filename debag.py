from pathlib import Path
from cst_service import CSTService
from test_free import CompleteASTService
from fsm_detector_service import FSMDetectorService

# 1) путь к файлу
sv_path = Path(r"C:\Users\Aushota\Downloads\03_01_detect_sequence_using_fsm.sv")
sv_text = sv_path.read_text(encoding="utf-8")

# 2) построить CST и AST
cst = CSTService().build_cst_from_text(sv_text, str(sv_path))
svc = CompleteASTService()
ast = svc.build_complete_ast_from_cst(cst)

# 3) сохранить модуль в файл
svc.save_fsm_detector_input(ast, "out/fsm_input.json", pretty=True)

# 4) загрузить и передать в детектор
payload = CompleteASTService.load_fsm_detector_input("out/fsm_input.json")
module_for_detector = payload["module"]

detector = FSMDetectorService()
fsm_info = detector.detect_finite_state_machines(module_for_detector, cst)  # ← добавили tree
print(fsm_info)
