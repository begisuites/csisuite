import numpy as np
from setuptools import setup, Extension
from Cython.Build import cythonize

if __name__ == "__main__":
    exts = [
        Extension(
            name="_nexmon_fast",
            sources=["_nexmon_fast.pyx"],
            include_dirs=[np.get_include()],
            extra_compile_args=["-O3"],   # optional
        )
    ]

    setup(
        name="_nexmon_fast",
        ext_modules=cythonize(exts, language_level="3"),
        extra_compile_args=["-O3", "-fopenmp"],
        extra_link_args=["-fopenmp"]
    )

# Compile with 'python _nexmon_fast_setup.py build_ext --inplace'