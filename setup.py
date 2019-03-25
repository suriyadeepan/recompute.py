import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="recompute",
    version="0.9.2",
    author="Suriyadeepan Ramamoorthy",
    author_email="suriyadeepan.r@gmail.com",
    description="Remote Computation Framework",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/suriyadeepan/recompute.py",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={
      'console_scripts' : [ 're=recompute.recompute:main' ],
      },
)
