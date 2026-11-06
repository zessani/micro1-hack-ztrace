from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext


class OptionalBuildExt(build_ext):
    def run(self):
        try:
            super().run()
        except Exception:
            self.extensions = []

    def build_extension(self, ext):
        try:
            super().build_extension(ext)
        except Exception:
            pass


setup(
    name="fastcsv",
    version="0.4.2",
    packages=["fastcsv"],
    ext_modules=[Extension("fastcsv._speedups", ["fastcsv/_speedups.c"], libraries=["zstd"])],
    cmdclass={"build_ext": OptionalBuildExt},
)
