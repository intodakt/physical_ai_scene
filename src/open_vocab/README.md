# S3 — Open-Vocabulary Perception

**Owner:** Student 3 (Li Yizhe). YOLO-World finds objects from text prompts, SAM 2 cuts out their
pixels. No training: pre-trained Ultralytics weights only.

> README drafted by S7 from the code during integration — S3, please correct anything that is off.

## Run
```bash
pip install -r requirements.txt            # needs ultralytics (+ torch)
python -m src.open_vocab.run --image <rgb.png> --config src/open_vocab/configs/desk.json --device cpu
python -m src.open_vocab.run --images <folder of frames> --config src/open_vocab/configs/desk.json
python -m src.open_vocab.run --video <clip.mp4> --prompts-file src/open_vocab/configs/unseen_objects.txt
python -m src.open_vocab.contract output/s3_semantic/<run>/frame_000000/observation.json   # validate
```
Weights (`yolov8s-worldv2.pt`, `sam2_t.pt`) are downloaded by Ultralytics on first use, or passed with
`--detector-weights` / `--sam-weights`. Results go to `output/s3_semantic/<UTC time>/` with a `run.json` manifest.

## Configs (`configs/`)
| File | Prompts |
|---|---|
| `desk.json` | laptop, coffee mug, keyboard, mouse, book, bottle (used by the G1 pipeline) |
| `zed_mini_left.json` | same model settings + ZED Mini left-camera input profile (default of `run.py`) |
| `tabletop.json`, `generic_tabletop.json` | other tabletop vocabularies |
| `unseen_objects.txt` | one prompt per line, for the open-vocabulary (unseen object) test |

## Output contract (to S2): `frame_XXXXXX/observation.json`
`schema_version: "s3-semantic-draft-0.1"`, `frame_id`, `timestamp`, `image_size`, and `detections[]` with
`detection_id`, `bbox` (xyxy, original pixels), `labels`, `detector_score`, `mask_status` (`ok`/`empty`/`missing`)
and `mask` (PNG path relative to the JSON, values 0/255). Full schema: `semantic_observation.schema.json`;
validator: `contract.py`. Also written: `annotated.jpg`, `segmentation.jpg`, `masks/det_XXXX.png`.

## In the G1 pipeline
`python main_pipeline.py --s3 live` runs this module on every frame (`configs/s7_integration.yaml: s3_config`);
the default `replay` mode reads `observation.json` files that S3 already wrote.
