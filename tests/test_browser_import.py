import shutil
import subprocess
from pathlib import Path

import pytest


NODE = shutil.which("node")
APP = Path(__file__).parents[1] / "src" / "chatdocket" / "static" / "app.js"


@pytest.mark.skipif(NODE is None, reason="Node.js is required for browser code tests")
def test_dropped_folder_reads_all_direct_files_but_not_nested_files():
    script = r'''
const fs = require("node:fs");
const source = fs.readFileSync(process.argv[1], "utf8");

function element() {
  return {
    classList: { add() {}, remove() {} },
    addEventListener() {},
    append() {},
    replaceChildren() {},
  };
}

global.document = {
  createElement: element,
  querySelector: element,
};
global.location = { href: "http://127.0.0.1/" };
const filesFromEntry = new Function(`${source}\nreturn filesFromEntry;`)();

function file(name) {
  return {
    isFile: true,
    isDirectory: false,
    file(resolve) { resolve({ name }); },
  };
}

function directory(entries) {
  let offset = 0;
  return {
    isFile: false,
    isDirectory: true,
    createReader() {
      return {
        readEntries(resolve) {
          const batch = entries.slice(offset, offset + 100);
          offset += batch.length;
          resolve(batch);
        },
      };
    },
  };
}

const nested = directory([file("nested.png")]);
const direct = Array.from({ length: 201 }, (_, index) => file(`chat-${index}.png`));
filesFromEntry(directory([nested, ...direct])).then((files) => {
  if (files.length !== 201 || files.some((item) => item.name === "nested.png")) {
    throw new Error(`unexpected files: ${files.map((item) => item.name).join(",")}`);
  }
});
'''

    result = subprocess.run(
        [NODE, "-e", script, str(APP)], capture_output=True, text=True, check=False
    )

    assert result.returncode == 0, result.stderr
