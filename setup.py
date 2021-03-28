from pathlib import Path
from setuptools import setup, find_packages

requirements = Path("requirements.txt").read_text().strip().splitlines()

pkg = "nextalbums"
setup(
    name=pkg,
    version="0.1.0",
    url="https://github.com/seanbreckenridge/albums",
    author="Sean Breckenridge",
    author_email="seanbrecke@gmail.com",
    description=("my personal album system"),
    license="MIT",
    packages=find_packages(include=[pkg]),
    entry_points={"console_scripts": ["nextalbums = nextalbums.__main__:main"]},
    install_requires=requirements,
)
