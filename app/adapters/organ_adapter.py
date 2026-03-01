import shutil
import subprocess
from pathlib import Path
from typing import Dict, List

import numpy as np
import SimpleITK as sitk
from PIL import Image

from app.adapters.base_adapter import BaseAdapter


class OrganAdapter(BaseAdapter):
    LUNG_ROIS = [
        "lung_upper_lobe_left",
        "lung_lower_lobe_left",
        "lung_upper_lobe_right",
        "lung_middle_lobe_right",
        "lung_lower_lobe_right",
    ]

    def __init__(
        self,
        job_id: str,
        targets: List[str],
        uploads_dir: Path,
        outputs_dir: Path,
        logs_path: Path,
    ) -> None:
        self.job_id = job_id
        self.targets = targets
        self.uploads_dir = Path(uploads_dir)
        self.outputs_dir = Path(outputs_dir)
        self.logs_path = Path(logs_path)

        self.job_output_dir = self.outputs_dir / self.job_id
        self.raw_output_dir = self.job_output_dir / "ts_raw"
        self.masks_dir = self.job_output_dir / "masks"
        self.previews_dir = self.job_output_dir / "previews"

        self.raw_output_dir.mkdir(parents=True, exist_ok=True)
        self.masks_dir.mkdir(parents=True, exist_ok=True)
        self.previews_dir.mkdir(parents=True, exist_ok=True)

        self._metrics: Dict[str, float] = {}

    def preprocess(self, input_path: Path) -> Path:
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        return input_path

    def _find_totalsegmentator_cli(self) -> str:
        for candidate in ("TotalSegmentator", "totalsegmentator"):
            if shutil.which(candidate):
                return candidate
        raise RuntimeError("TotalSegmentator CLI was not found in PATH")

    def infer(self, processed_path: Path) -> Path:
        cli = self._find_totalsegmentator_cli()

        roi_subset: List[str] = []
        if "lungs" in self.targets:
            roi_subset.extend(self.LUNG_ROIS)
        if "liver" in self.targets:
            roi_subset.append("liver")

        cmd = [cli, "-i", str(processed_path), "-o", str(self.raw_output_dir)]
        if roi_subset:
            cmd.extend(["--roi_subset", *roi_subset])

        with self.logs_path.open("a", encoding="utf-8") as log_file:
            log_file.write("\n=== TotalSegmentator Command ===\n")
            log_file.write(" ".join(cmd) + "\n")
            completed = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            if completed.stdout:
                log_file.write("\n=== STDOUT ===\n")
                log_file.write(completed.stdout)
            if completed.stderr:
                log_file.write("\n=== STDERR ===\n")
                log_file.write(completed.stderr)

        if completed.returncode != 0:
            raise RuntimeError(
                f"TotalSegmentator failed with return code {completed.returncode}. See logs.txt for details."
            )

        return self.raw_output_dir

    def postprocess(self, prediction_path: Path) -> Dict[str, Path]:
        mask_paths: Dict[str, Path] = {}

        if "lungs" in self.targets:
            lung_roi_files = [prediction_path / f"{roi}.nii.gz" for roi in self.LUNG_ROIS]
            existing = [path for path in lung_roi_files if path.exists()]
            if not existing:
                raise RuntimeError("TotalSegmentator output is missing lung ROI masks")

            combined_mask = None
            reference_image = None
            for mask_file in existing:
                mask_image = sitk.ReadImage(str(mask_file))
                mask_array = sitk.GetArrayFromImage(mask_image) > 0
                if combined_mask is None:
                    combined_mask = mask_array
                    reference_image = mask_image
                else:
                    combined_mask = np.logical_or(combined_mask, mask_array)

            if combined_mask is None or reference_image is None:
                raise RuntimeError("Unable to construct lungs mask")

            lungs_mask_image = sitk.GetImageFromArray(combined_mask.astype(np.uint8))
            lungs_mask_image.CopyInformation(reference_image)
            lungs_output = self.masks_dir / "lungs.nii.gz"
            sitk.WriteImage(lungs_mask_image, str(lungs_output))
            mask_paths["lungs"] = lungs_output

        if "liver" in self.targets:
            liver_source = prediction_path / "liver.nii.gz"
            if not liver_source.exists():
                raise RuntimeError("TotalSegmentator output is missing liver.nii.gz")

            liver_image = sitk.ReadImage(str(liver_source))
            liver_mask = sitk.GetArrayFromImage(liver_image) > 0
            liver_output_image = sitk.GetImageFromArray(liver_mask.astype(np.uint8))
            liver_output_image.CopyInformation(liver_image)
            liver_output = self.masks_dir / "liver.nii.gz"
            sitk.WriteImage(liver_output_image, str(liver_output))
            mask_paths["liver"] = liver_output

        return mask_paths

    def generate_previews(self, input_path: Path, mask_paths_dict: Dict[str, Path]) -> List[Path]:
        if not mask_paths_dict:
            return []

        ct_image = sitk.DICOMOrient(sitk.ReadImage(str(input_path)), "LPS")
        ct_array = sitk.GetArrayFromImage(ct_image).astype(np.float32)

        union_mask = np.zeros_like(ct_array, dtype=bool)
        for mask_path in mask_paths_dict.values():
            mask_image = sitk.DICOMOrient(sitk.ReadImage(str(mask_path)), "LPS")
            mask_array = sitk.GetArrayFromImage(mask_image) > 0
            if mask_array.shape != union_mask.shape:
                raise RuntimeError("Mask and input volume shapes do not match for preview generation")
            union_mask = np.logical_or(union_mask, mask_array)

        # ct_array and union_mask are [z, y, x] after LPS orientation.
        if np.any(union_mask):
            axial_index = int(np.argmax(np.sum(union_mask, axis=(1, 2))))
            sagittal_index = int(np.argmax(np.sum(union_mask, axis=(0, 1))))
            coronal_index = int(np.argmax(np.sum(union_mask, axis=(0, 2))))
        else:
            z_dim, y_dim, x_dim = ct_array.shape
            axial_index = z_dim // 2
            sagittal_index = x_dim // 2
            coronal_index = y_dim // 2

        plane_slices = [
            ("axial", ct_array[axial_index, :, :], union_mask[axial_index, :, :]),
            ("sagittal", ct_array[:, :, sagittal_index], union_mask[:, :, sagittal_index]),
            ("coronal", ct_array[:, coronal_index, :], union_mask[:, coronal_index, :]),
        ]

        preview_paths: List[Path] = []
        for idx, (_plane_name, ct_slice, mask_slice) in enumerate(plane_slices):
            ct_slice = np.flipud(ct_slice)
            mask_slice = np.flipud(mask_slice)

            p1, p99 = np.percentile(ct_slice, [1, 99])
            if p99 <= p1:
                p1 = float(np.min(ct_slice))
                p99 = float(np.max(ct_slice))
            if p99 <= p1:
                p99 = p1 + 1.0

            normalized = np.clip(ct_slice, p1, p99)
            normalized = ((normalized - p1) / (p99 - p1) * 255.0).astype(np.uint8)

            rgb = np.stack([normalized, normalized, normalized], axis=-1).astype(np.float32)
            alpha = 0.35
            rgb[mask_slice, 0] = (1.0 - alpha) * rgb[mask_slice, 0] + alpha * 255.0
            rgb[mask_slice, 1] = (1.0 - alpha) * rgb[mask_slice, 1]
            rgb[mask_slice, 2] = (1.0 - alpha) * rgb[mask_slice, 2]

            preview_image = Image.fromarray(rgb.astype(np.uint8), mode="RGB")
            preview_path = self.previews_dir / f"overlay_{idx}.png"
            preview_image.save(preview_path)
            preview_paths.append(preview_path)

        return preview_paths

    def return_metrics(self) -> Dict[str, float]:
        return self._metrics
