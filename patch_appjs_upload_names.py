#!/usr/bin/env python3
"""
Патч Rocket.Chat app.js (~8.3.x):

1) uploadsOnValidate — как раньше: транслит кириллицы, пробелы/мусор → дефис, update в коллекцию.

2) sendFileMessage: после Uploads.updateFileComplete(...) клиент может перезаписать name;
   перед сборкой attachment снова применяем ту же санитизацию к file.name — иначе в UI «title»
   остаётся с русскими символами (как у тебя на скрине).

3) visitor livechat отправка файла — санитизация перед build attachment.

Повторный запуск безопасен: пропускает уже изменённые блоки по маркерам.
Исходный файл — vanilla с образа тем же скриптом что и патч версии образа.
"""

from __future__ import annotations

import json
import sys

# ----- 1. Начало uploadsOnValidate в vanilla 8.3.2
NEEDLE_UPLOADS = """      async uploadsOnValidate(file, options) {
        if (!file.type || !/^image\\/((x-windows-)?bmp|p?jpeg|png|gif|webp)$/.test(file.type)) {
          return;
        }"""

MARK_SENDFILE_PATCH = "/* rc-patch: sendFileMessage sanitize file.name */"
MARK_LIVECHAT_PATCH = "/* rc-patch: livechat visitor sanitize file.name */"

# ----- 2. sendFileMessage / parseFileIntoMessageAttachments (ровно один такой блок в бандле 8.3.2)
NEEDLE_UPDATE_COMPLETE = """      await Uploads.updateFileComplete(file._id, user._id, omit(file, '_id'));
      const fileUrl = FileUpload.getPath("".concat(file._id, "/").concat(encodeURI(file.name || '')));"""

# ----- 3. livechat visitor: ряд «const fileUrl = file.name && FileUpload...»
NEEDLE_LIVECHAT = """      const fileUrl = file.name && FileUpload.getPath("".concat(file._id, "/").concat(encodeURI(file.name)));
      const attachment = {
        title: file.name,"""


def build_cyrillic_map() -> dict[str, str]:
    rus = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
    lat = (
        "a",
        "b",
        "v",
        "g",
        "d",
        "e",
        "yo",
        "zh",
        "z",
        "i",
        "j",
        "k",
        "l",
        "m",
        "n",
        "o",
        "p",
        "r",
        "s",
        "t",
        "u",
        "f",
        "kh",
        "ts",
        "ch",
        "sh",
        "sch",
        "",
        "y",
        "",
        "e",
        "yu",
        "ya",
    )
    assert len(rus) == len(lat) == 33
    m: dict[str, str] = {}
    for rc, lk in zip(rus, lat):
        m[rc] = lk
        u = rc.upper()
        if u != rc:
            m[u] = lk
    return m


def js_json_map() -> str:
    inner = json.dumps(build_cyrillic_map(), ensure_ascii=True, separators=(",", ":"))
    return "JSON.parse(" + json.dumps(inner) + ")"


def block_uploads_on_validate() -> str:
    jm = js_json_map()
    return f"""      async uploadsOnValidate(file, options) {{
        const CYR_MAP = {jm};
        const sanitizeUploadFileName = raw => {{
          if (typeof raw !== "string" || !raw) return raw;
          const src = raw.normalize("NFC").trim();
          const dotIdx = src.lastIndexOf(".");
          const hasExt = dotIdx > 0;
          let stem = hasExt ? src.slice(0, dotIdx) : src;
          let extLetters = "";
          if (hasExt) {{
            extLetters = "".concat(src.slice(dotIdx + 1).replace(/[^a-zA-Z0-9]/g, "").toLowerCase()).slice(0, 32);
          }}
          let merged = "";
          for (let j = 0; j < stem.length; j++) {{
            const ch = stem[j];
            const mapped = CYR_MAP[ch];
            merged += mapped !== undefined ? mapped : ch;
          }}
          merged = merged.replace(/\\s+/g, "-").replace(/[^a-zA-Z0-9-]/g, "-").toLowerCase();
          merged = merged.replace(/-+/g, "-").replace(/^-|-$/g, "");
          if (!merged.length) {{
            merged = "file";
          }}
          const extSuffix = extLetters !== "" ? "".concat(".", extLetters) : "";
          return "".concat(merged, extSuffix);
        }};
        const normalizedUploadName = sanitizeUploadFileName(file.name || "");
        if (normalizedUploadName && normalizedUploadName !== file.name) {{
          await this.getCollection().updateOne({{ _id: file._id }}, {{ $set: {{ name: normalizedUploadName }} }}, options);
          file.name = normalizedUploadName;
        }}
        if (!file.type || !/^image\\/((x-windows-)?bmp|p?jpeg|png|gif|webp)$/.test(file.type)) {{
          return;
        }}"""


def block_iife_assign_file_name(mark_comment: str) -> str:
    """Перезаписать file.name (IIFE, свой CYR_MAP в каждой вставке)."""
    jm = js_json_map()
    return f"""{mark_comment}
      file.name = (raw => {{
        const CYR_MAP = {jm};
        if (typeof raw !== "string" || !raw) return raw;
        const src = raw.normalize("NFC").trim();
        const dotIdx = src.lastIndexOf(".");
        const hasExt = dotIdx > 0;
        let stem = hasExt ? src.slice(0, dotIdx) : src;
        let extLetters = "";
        if (hasExt) {{
          extLetters = "".concat(src.slice(dotIdx + 1).replace(/[^a-zA-Z0-9]/g, "").toLowerCase()).slice(0, 32);
        }}
        let merged = "";
        for (let j = 0; j < stem.length; j++) {{
          const ch = stem[j];
          const mapped = CYR_MAP[ch];
          merged += mapped !== undefined ? mapped : ch;
        }}
        merged = merged.replace(/\\s+/g, "-").replace(/[^a-zA-Z0-9-]/g, "-").toLowerCase();
        merged = merged.replace(/-+/g, "-").replace(/^-|-$/g, "");
        if (!merged.length) {{
          merged = "file";
        }}
        const extSuffix = extLetters !== "" ? "".concat(".", extLetters) : "";
        return "".concat(merged, extSuffix);
      }})(file.name || "") || file.name"""


def needle_sendfile_replace() -> str:
    return (
        """      await Uploads.updateFileComplete(file._id, user._id, omit(file, '_id'));"""
        + "\n"
        + block_iife_assign_file_name(MARK_SENDFILE_PATCH)
        + "\n"
        + """      const fileUrl = FileUpload.getPath("".concat(file._id, "/").concat(encodeURI(file.name || '')));"""
    )


def needle_livechat_replace() -> str:
    return (
        block_iife_assign_file_name(MARK_LIVECHAT_PATCH)
        + "\n"
        + """      const fileUrl = file.name && FileUpload.getPath("".concat(file._id, "/").concat(encodeURI(file.name)));
      const attachment = {
        title: file.name,"""
    )


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: patch_appjs_upload_names.py /path/to/app.js", file=sys.stderr)
        sys.exit(2)
    path = sys.argv[1]
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        data = f.read()
    out = data
    changed = 0

    if NEEDLE_UPLOADS in out:
        out2 = out.replace(NEEDLE_UPLOADS, block_uploads_on_validate(), 1)
        if out2 != out:
            out = out2
            changed += 1

    if NEEDLE_UPDATE_COMPLETE in out and MARK_SENDFILE_PATCH not in out:
        out2 = out.replace(NEEDLE_UPDATE_COMPLETE, needle_sendfile_replace(), 1)
        if out2 != out:
            out = out2
            changed += 1

    if NEEDLE_LIVECHAT in out:
        pos = out.find(NEEDLE_LIVECHAT)
        if pos >= 0:
            win = out[max(0, pos - 320) : pos]
            if MARK_LIVECHAT_PATCH not in win:
                out2 = out.replace(NEEDLE_LIVECHAT, needle_livechat_replace(), 1)
                if out2 != out:
                    out = out2
                    changed += 1

    if out == data:
        print("no changes (уже пропатчено или нет подходящих якорей)", file=sys.stderr)
        sys.exit(1)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(out)
    print(f"patched ok ({changed} блок(ов))")


if __name__ == "__main__":
    main()
