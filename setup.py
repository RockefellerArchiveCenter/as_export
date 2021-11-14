from setuptools import find_packages, setup

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="as_export",
    url="https://github.com/RockefellerArchiveCenter/as_export",
    description="Exports EAD and METS files from updated description in ArchivesSpace.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Rockefeller Archive Center",
    author_email="archive@rockarch.org",
    version="1.0",
    license='MIT',
    packages=find_packages(),
    zip_safe=False,
    classifiers=[
        'Programming Language :: Python :: 3',
        'Intended Audience :: Other Audience',
        'License :: OSI Approved :: MIT License',
    ],
    python_requires=">=2.7",
    install_requires=[
        "ArchivesSnake",
        "requests-toolbelt",
    ],
)
