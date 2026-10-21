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
from PIL import Image
from pydantic import TypeAdapter, ValidationError
from rapidocr import RapidOCR
from starlette.formparsers import MultiPartParser

MultiPartParser.max_part_size = 10 * 1024 * 1024  # 10MB
MultiPartParser.max_file_size = 20 * 1024 * 1024   # 20MB
sys.path.append(str(Path(__file__).resolve().parent.parent))


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

        # RapidOCR 会把调用时传入的 use_* 写回实例，并发请求共用一个实例时会互相覆盖。
        # 因此每种 use_* 组合各建一个实例，调用时不再传 use_*；模型在实例首次使用时才加载
        self.ocr_by_flags = {
            flags: RapidOCR(
                params={
                    **params,
                    "Global.use_det": flags[0],
                    "Global.use_cls": flags[1],
                    "Global.use_rec": flags[2],
                }
            )
            for flags in itertools.product([True, False], repeat=3)
        }
        # 未传的 use_* 沿用 rapidocr 配置里的默认值
        default_ocr = RapidOCR(params=params)
        self.default_flags = (default_ocr.use_det, default_ocr.use_cls, default_ocr.use_rec)

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
            img = np.array(ori_img)
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

        out_dict = {}
        for i in range(num):
            values = {}
            if txts is not None:
                values["rec_txt"] = txts[i]
            if boxes is not None:
                values["dt_boxes"] = boxes[i].tolist()
            if scores is not None:
                values["score"] = float(scores[i])
            out_dict[i] = values
        return out_dict


def parse_form_bool(value: Optional[str]) -> Optional[bool]:
    # fastapi>=0.147 会把未传的 bool 表单字段当成 False，所以改用 str 接收，未传时保持 None
    if value is None:
        return None
    try:
        return TypeAdapter(bool).validate_python(value)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


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
    if image_file:
        img = Image.open(image_file.file)
    elif image_data:
        img_bytes = str.encode(image_data)
        img_b64decode = base64.b64decode(img_bytes)
        img = Image.open(io.BytesIO(img_b64decode))
    else:
        raise ValueError(
            "When sending a post request, data or files must have a value."
        )
    ocr_res = processor(
        img,
        use_det=parse_form_bool(use_det),
        use_cls=parse_form_bool(use_cls),
        use_rec=parse_form_bool(use_rec),
    )

    return ocr_res


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
