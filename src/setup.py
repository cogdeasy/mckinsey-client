import os

from setuptools import find_packages, setup

HERE = os.path.abspath(os.path.dirname(__file__))

# Packaging kept deliberately simple: the asset is installed with `pip install -e src`
# from the engagement laptop image, which still ships setuptools 44. -- JL

entry_point = "meridian = meridian.run:run_package"


with open(os.path.join(HERE, os.pardir, "README.md"), "r") as fh:
    long_description = fh.read()

with open(os.path.join(HERE, "requirements.txt"), "r") as f:
    requires = [
        line.strip()
        for line in f
        if line.strip() and not line.strip().startswith("#")
    ]

setup(
    name="meridian",
    version="2.4.1",
    description="Meridian demand forecasting asset (Nordfalk deployment)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    python_requires=">=3.8, <3.9",
    packages=find_packages(exclude=["tests"]),
    entry_points={"console_scripts": [entry_point]},
    install_requires=requires,
    extras_require={
        "docs": [
            "sphinx~=3.4.3",
            "sphinx_rtd_theme==0.5.1",
            "nbsphinx==0.8.1",
        ]
    },
    include_package_data=True,
    package_data={
        "meridian": [
            "resources/*.yml",
            "resources/*.csv",
        ]
    },
)
