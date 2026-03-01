from pathlib import Path
from typing import Dict, List


class BaseAdapter:
    def preprocess(self, input_path: Path) -> Path:
        raise NotImplementedError

    def infer(self, processed_path: Path) -> Path:
        raise NotImplementedError

    def postprocess(self, prediction_path: Path) -> Dict[str, Path]:
        raise NotImplementedError

    def generate_previews(self, input_path: Path, mask_paths_dict: Dict[str, Path]) -> List[Path]:
        raise NotImplementedError

    def return_metrics(self) -> Dict[str, float]:
        raise NotImplementedError
