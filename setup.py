import os
from pathlib import Path

from setuptools import setup

ext_modules = []
if os.environ.get("ONETIPS_MYPYC") == "1":
    from mypyc.build import mypycify

    core = sorted(path.as_posix() for path in Path("src/onetips/core").rglob("*.py") if path.name != "__init__.py")
    ext_modules = mypycify(["--strict", *core])

setup(ext_modules=ext_modules)
