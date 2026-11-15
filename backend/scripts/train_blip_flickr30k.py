"""Fine-tune BLIP on Flickr30k's human-written image captions with RAM safety guards.

Run from the backend directory:
    python scripts/train_blip_flickr30k.py

Features:
- RAM Watchdog: Uses psutil to monitor memory and abort cleanly before OOM crash.
- CPU Thread Optimization: Avoids thread contention on multi-core CPUs.
- Frozen Vision Backbone: Updates only language projection & cross-attention heads.
- Automatic Export: Saves processor and weights directly to models/blip-flickr30k.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import psutil
import torch
from datasets import load_dataset
from PIL import Image
from transformers import (
    BlipForConditionalGeneration,
    BlipProcessor,
    Trainer,
    TrainerCallback,
    TrainingArguments,
)

# CPU thread optimization
torch.set_num_threads(min(4, os.cpu_count() or 4))

BASE_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = Path(
    os.getenv("BLIP_OUTPUT_DIR", str(BASE_DIR / "models" / "blip-flickr30k"))
)
BASE_MODEL = os.getenv("BLIP_BASE_MODEL", "Salesforce/blip-image-captioning-base")
DATASET_NAME = os.getenv("BLIP_DATASET", "nlphuji/flickr30k")
MAX_TRAIN_SAMPLES = int(os.getenv("BLIP_MAX_TRAIN_SAMPLES", "200"))
MAX_EVAL_SAMPLES = int(os.getenv("BLIP_MAX_EVAL_SAMPLES", "50"))
MAX_RAM_PERCENT = float(os.getenv("BLIP_MAX_RAM_PERCENT", "85.0"))


def check_system_ram(stage: str = "") -> None:
    vm = psutil.virtual_memory()
    used_gb = vm.used / (1024**3)
    total_gb = vm.total / (1024**3)
    percent = vm.percent
    print(f"[RAM Monitor {stage}] Using {used_gb:.2f} GB / {total_gb:.2f} GB ({percent}%)")
    if percent > MAX_RAM_PERCENT:
        raise MemoryError(
            f"RAM usage ({percent}%) exceeded safety limit ({MAX_RAM_PERCENT}%). "
            "Stopping training to prevent system freeze or reboot."
        )


class RamWatchdogCallback(TrainerCallback):
    def on_step_end(self, args, state, control, **kwargs):
        if state.global_step % 10 == 0:
            try:
                check_system_ram(f"Step {state.global_step}")
            except MemoryError as exc:
                print(f"\n[ALERT] {exc}")
                print("Triggering emergency early stop and checkpoint save...")
                control.should_training_stop = True


def _caption_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list) and value:
        first = value[0]
        if isinstance(first, dict):
            return str(first.get("raw") or first.get("caption") or first.get("text") or "")
        return str(first)
    if isinstance(value, dict):
        return str(value.get("raw") or value.get("caption") or value.get("text") or "")
    return ""


def main() -> None:
    print("=== BLIP Caption Fine-Tuning Pipeline ===")
    check_system_ram("Start")

    print(f"Loading base model: {BASE_MODEL}...")
    processor = BlipProcessor.from_pretrained(BASE_MODEL)
    model = BlipForConditionalGeneration.from_pretrained(BASE_MODEL)
    model.gradient_checkpointing_enable()

    # Freeze vision encoder to preserve features and save memory
    for parameter in model.vision_model.parameters():
        parameter.requires_grad = False
    print("Vision encoder successfully frozen.")

    try:
        print(f"Loading dataset: {DATASET_NAME}...")
        dataset = load_dataset(DATASET_NAME)
    except RuntimeError as exc:
        if "Dataset scripts are no longer supported" in str(exc):
            raise RuntimeError(
                "Flickr30k requires datasets==3.6.0. Reinstall backend requirements."
            ) from exc
        raise

    split = dataset["train"] if "train" in dataset else next(iter(dataset.values()))
    split = split.filter(lambda item: bool(_caption_text(item.get("caption"))))
    split = split.train_test_split(test_size=0.1, seed=42)

    split["train"] = split["train"].select(
        range(min(MAX_TRAIN_SAMPLES, len(split["train"])))
    )
    split["test"] = split["test"].select(
        range(min(MAX_EVAL_SAMPLES, len(split["test"])))
    )
    print(f"Prepared {len(split['train'])} train samples and {len(split['test'])} validation samples.")

    check_system_ram("Post-Dataset Load")

    def prepare(item: dict[str, Any]) -> dict[str, Any]:
        image = item["image"].convert("RGB") if isinstance(item["image"], Image.Image) else item["image"]
        encoded = processor(
            images=image,
            text=_caption_text(item["caption"]),
            padding="max_length",
            truncation=True,
            max_length=64,
        )
        return {
            "pixel_values": encoded["pixel_values"][0],
            "input_ids": encoded["input_ids"][0],
            "attention_mask": encoded["attention_mask"][0],
            "labels": encoded["input_ids"][0],
        }

    encoded = split.map(
        prepare,
        remove_columns=split["train"].column_names,
        desc="Tokenizing image-caption pairs",
    )
    encoded.set_format("torch")

    args = TrainingArguments(
        output_dir=str(OUTPUT_DIR),
        per_device_train_batch_size=int(os.getenv("BLIP_BATCH_SIZE", "1")),
        per_device_eval_batch_size=int(os.getenv("BLIP_EVAL_BATCH_SIZE", "1")),
        gradient_accumulation_steps=int(os.getenv("BLIP_GRADIENT_ACCUMULATION", "16")),
        learning_rate=float(os.getenv("BLIP_LEARNING_RATE", "5e-6")),
        num_train_epochs=float(os.getenv("BLIP_EPOCHS", "1")),
        max_steps=int(os.getenv("BLIP_MAX_STEPS", "100")),
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        fp16=False,
        use_cpu=True,
        dataloader_num_workers=0,
        dataloader_pin_memory=False,
        max_grad_norm=1.0,
        logging_steps=20,
        save_total_limit=2,
        report_to="none",
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=encoded["train"],
        eval_dataset=encoded["test"],
        callbacks=[RamWatchdogCallback()],
    )

    print("Starting training with RAM watchdog active...")
    trainer.train()

    print(f"Saving fine-tuned BLIP model to {OUTPUT_DIR}...")
    trainer.save_model(str(OUTPUT_DIR))
    processor.save_pretrained(str(OUTPUT_DIR))
    print("Done! The API will automatically prioritize this fine-tuned model upon restart.")


if __name__ == "__main__":
    main()
