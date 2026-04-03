"""Setup for ScribeBox."""

from setuptools import setup, find_packages

setup(
    name="scribebox",
    version="0.1.0",
    description="USB-bootable transcription appliance",
    packages=find_packages(),
    python_requires=">=3.10",
    entry_points={
        "console_scripts": [
            "scribebox=scribebox.__main__:main",
        ],
    },
)
