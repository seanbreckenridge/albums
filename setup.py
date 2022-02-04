from pathlib import Path
from setuptools import setup, find_packages


requirements = Path("requirements.txt").read_text().strip().splitlines()
pkg = "nextalbums"

if __name__ == "__main__":
    setup(
        name=pkg,
        url="https://github.com/seanbreckenridge/albums",
        use_scm_version={
            "local_scheme": "dirty-tag",
        },
        zip_safe=False,
        author="Sean Breckenridge",
        author_email="seanbrecke@gmail.com",
        description=("my personal album system"),
        license="MIT",
        packages=find_packages(include=[pkg]),
        entry_points={"console_scripts": ["nextalbums = nextalbums.__main__:main"]},
        package_data={pkg: ["py.typed"]},
        install_requires=requirements,
    )
