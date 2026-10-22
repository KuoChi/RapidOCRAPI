# -*- encoding: utf-8 -*-
# @Author: SWHL
# @Contact: liekkaskono@163.com
import argparse
import base64
import io
import itertools
import os
import sys
import threading
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import uvicorn
from fastapi import FastAPI, Form, HTTPException, UploadFile
from fastapi.exceptions import RequestValidationError
from PIL import Image
from pydantic import TypeAdapter, ValidationError
from rapidocr import RapidOCR
from starlette.formparsers import MultiPartParser

MultiPartParser.max_part_size = 10 * 1024 * 1024  # 10MB
MultiPartParser.max_file_size = 20 * 1024 * 1024   # 20MB
sys.path.append(str(Path(__file__).resolve().parent.parent))

BOOL_ADAPTER = TypeAdapter(bool)


class InvalidImageError(ValueError):
    pass


class OCRAPIUtils:
    def __init__(self) -> None:
        det_model_path = os.getenv("det_model_path", None)
        cls_model_path = os.getenv("cls_model_path", None)
        rec_model_path = os.getenv("rec_model_path", None)

        params = {}
        if not (det_model_path is None or cls_model_path is None or rec_model_path is None):
            params = {
                "Det.model_path": det_model_path,
                "Cls.model_path": cls_model_path,
                "Rec.model_path": rec_model_path,
            }

        # 未传的 use_* 沿用 rapidocr 配置里的默认值
        default_ocr = RapidOCR(params=params)
        self.default_flags = (default_ocr.use_det, default_ocr.use_cls, default_ocr.use_rec)

        # RapidOCR 会把调用时传入的 use_* 写回实例，并发请求共用一个实例时会互相覆盖。
        # 因此每种 use_* 组合各建一个实例，调用时不再传 use_*；模型在实例首次使用时才加载
        self.ocr_by_flags = {self.default_flags: default_ocr}
        for flags in itertools.product([True, False], repeat=3):
            if flags not in self.ocr_by_flags:
                self.ocr_by_flags[flags] = RapidOCR(
                    params={
                        **params,
                        "Global.use_det": flags[0],
                        "Global.use_cls": flags[1],
                        "Global.use_rec": flags[2],
                    }
                )

        # 限制同时进行的图片解码与推理数量，避免并发请求过多时内存暴涨；默认等于 CPU 数
        max_concurrency = int(os.getenv("ocr_max_concurrency", os.cpu_count() or 1))
        if max_concurrency < 1:
            raise ValueError("ocr_max_concurrency must be >= 1")
        self.semaphore = threading.BoundedSemaphore(max_concurrency)

    def __call__(
            self, ori_img: Image.Image, use_det=None, use_cls=None, use_rec=None
    ) -> Dict:
        flags = tuple(
            default if flag is None else flag
            for flag, default in zip((use_det, use_cls, use_rec), self.default_flags)
        )
        with self.semaphore:
            try:
                # 图片在这一步才真正解码，截断的图片会在这里报错
                img = np.array(ori_img)
            except OSError as e:
                raise InvalidImageError("Invalid image.") from e
            # 不传任何参数：RapidOCR 会把调用参数写回共用实例，并发时互相干扰
            ocr_res = self.ocr_by_flags[flags](img)

        # use_rec=False 时返回 TextDetOutput（没有 txts），use_det=False 时返回 TextRecOutput（没有 boxes），
        # 只做分类时返回 TextClsOutput（没有 boxes 和 txts）
        boxes = getattr(ocr_res, "boxes", None)
        txts = getattr(ocr_res, "txts", None)
        scores = getattr(ocr_res, "scores", None)
        if boxes is not None:
            num = len(boxes)
        elif txts is not None:
            num = len(txts)
        else:
            return {}
        # 只做检测时 scores 是检测框的置信度，用 det_score 与识别置信度 score 区分
        score_key = "score" if txts is not None else "det_score"

        out_dict = {}
        for i in range(num):
            values = {}
            if txts is not None:
                values["rec_txt"] = txts[i]
            if boxes is not None:
                values["dt_boxes"] = boxes[i].tolist()
            if scores is not None:
                values[score_key] = float(scores[i])
            out_dict[i] = values
        return out_dict


def parse_form_bools(**values: Optional[str]) -> Dict[str, Optional[bool]]:
    # fastapi>=0.147 会把未传的 bool 表单字段当成 False，所以改用 str 接收，未传时保持 None；
    # 不合法的值按 FastAPI 原生格式一次回报所有字段的 422
    parsed, errors = {}, []
    for field, value in values.items():
        try:
            parsed[field] = None if value is None else BOOL_ADAPTER.validate_python(value)
        except ValidationError as e:
            errors += [{**err, "loc": ("body", field)} for err in e.errors(include_url=False)]
    if errors:
        raise RequestValidationError(errors)
    return parsed


def load_image(image_file: Optional[UploadFile], image_data: Optional[str]) -> Image.Image:
    try:
        if image_file:
            return Image.open(image_file.file)
        return Image.open(io.BytesIO(base64.b64decode(image_data)))
    except (OSError, ValueError, Image.DecompressionBombError) as e:
        raise InvalidImageError("Invalid image.") from e


app = FastAPI()
processor = OCRAPIUtils()


@app.get("/")
def root():
    return {"message": "Welcome to RapidOCR API Server!"}


@app.post("/ocr")
def ocr(
        image_file: Optional[UploadFile] = None,
        image_data: str = Form(None),
        use_det: Optional[str] = Form(None),
        use_cls: Optional[str] = Form(None),
        use_rec: Optional[str] = Form(None),
):
    flags = parse_form_bools(use_det=use_det, use_cls=use_cls, use_rec=use_rec)
    if not image_file and not image_data:
        raise HTTPException(
            status_code=400, detail="Either image_file or image_data is required."
        )
    try:
        img = load_image(image_file, image_data)
        return processor(img, **flags)
    except InvalidImageError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


def main():
    parser = argparse.ArgumentParser("rapidocr_api")
    parser.add_argument("-ip", "--ip", type=str, default="0.0.0.0", help="IP Address")
    parser.add_argument("-p", "--port", type=int, default=9003, help="IP port")
    parser.add_argument(
        "-workers", "--workers", type=int, default=1, help="number of worker process"
    )
    args = parser.parse_args()

    # 修改 uvicorn 的默认日志配置
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["access"]["fmt"] = "%(asctime)s %(levelname)s %(message)s"
    log_config["formatters"]["default"]["fmt"] = "%(asctime)s %(levelname)s %(message)s"

    uvicorn.run(
        "rapidocr_api.main:app",
        host=args.ip,
        port=args.port,
        reload=False,
        workers=args.workers,
        log_config=log_config,
    )


if __name__ == "__main__":
    main()
