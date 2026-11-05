"""Copia timeline.json a composition/assets/data.js (la composición no lee archivos en el render)."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TL = json.loads((HERE / "timeline.json").read_text())
(HERE / "composition/assets/data.js").write_text("// Generado por build_data.py\nwindow.M4 = " + json.dumps(TL, ensure_ascii=False) + ";\n")
print("cuadros:", len(TL["cuadros"]))
