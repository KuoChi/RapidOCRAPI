import io
import itertools
import random
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from rapidocr_api.main import app

IMG_PATH = Path(__file__).parent / "test_files" / "ch_en_num.jpg"
FIRST_LINE_TXT = "大桶装更划算"

FULL_KEYS = {"rec_txt", "dt_boxes", "score"}
DET_KEYS = {"dt_boxes", "score"}
REC_KEYS = {"rec_txt", "score"}

client = TestClient(app)


def post_ocr(img_bytes: bytes, data=None):
    files = {"image_file": ("img.jpg", img_bytes, "image/jpeg")}
    return client.post("/ocr", files=files, data=data or {})


def item_keys(body: dict) -> set:
    return {key for item in body.values() for key in item}


@pytest.fixture(scope="module")
def full_img() -> bytes:
    return IMG_PATH.read_bytes()


@pytest.fixture(scope="module")
def line_img(full_img) -> bytes:
    """Crop the first detected text line, for use_det=false (single-line recognition)."""
    body = post_ocr(full_img).json()
    first = body["0"]
    assert first["rec_txt"] == FIRST_LINE_TXT
    xs = [p[0] for p in first["dt_boxes"]]
    ys = [p[1] for p in first["dt_boxes"]]
    buf = io.BytesIO()
    Image.open(IMG_PATH).crop((min(xs), min(ys), max(xs), max(ys))).save(buf, "PNG")
    return buf.getvalue()


def test_no_flags_returns_full_result(full_img):
    resp = post_ocr(full_img)

    assert resp.status_code == 200
    body = resp.json()
    assert body
    assert item_keys(body) == FULL_KEYS
    assert FIRST_LINE_TXT in [item["rec_txt"] for item in body.values()]


@pytest.mark.parametrize(
    "use_det,use_cls,use_rec", list(itertools.product([True, False], repeat=3))
)
def test_flag_combinations(full_img, line_img, use_det, use_cls, use_rec):
    data = {
        "use_det": str(use_det).lower(),
        "use_cls": str(use_cls).lower(),
        "use_rec": str(use_rec).lower(),
    }
    # use_det=false 只适合单行文字图片
    resp = post_ocr(full_img if use_det else line_img, data)

    assert resp.status_code == 200
    body = resp.json()
    if use_det and use_rec:
        assert body and item_keys(body) == FULL_KEYS
    elif use_det:
        assert body and item_keys(body) == DET_KEYS
    elif use_rec:
        assert item_keys(body) == REC_KEYS
        assert [item["rec_txt"] for item in body.values()] == [FIRST_LINE_TXT]
    else:
        assert body == {}


@pytest.mark.parametrize("field", ["use_det", "use_cls", "use_rec"])
def test_invalid_flag_returns_422(full_img, field):
    resp = post_ocr(full_img, {field: "abc"})

    assert resp.status_code == 422


@pytest.mark.parametrize("flag", ["use_rec", "use_det", "use_cls"])
def test_flags_do_not_leak_into_next_request(full_img, flag):
    post_ocr(full_img, {flag: "false"})

    body = post_ocr(full_img).json()

    assert body and item_keys(body) == FULL_KEYS


def test_concurrent_requests_with_different_flags(full_img):
    modes = {"full": {}, "det": {"use_rec": "false"}, "nocls": {"use_cls": "false"}}
    expected = {name: post_ocr(full_img, data).json() for name, data in modes.items()}
    # 先确认基准结果本身正确，避免旗标残留时拿错误的基准来比对
    assert item_keys(expected["full"]) == FULL_KEYS
    assert item_keys(expected["det"]) == DET_KEYS
    assert item_keys(expected["nocls"]) == FULL_KEYS
    random.seed(0)
    names = [random.choice(list(modes)) for _ in range(40)]

    def run(name):
        resp = post_ocr(full_img, modes[name])
        return name, resp.status_code, resp.json()

    with ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(run, names))

    mismatched = [name for name, code, body in results if code != 200 or body != expected[name]]
    assert mismatched == []
