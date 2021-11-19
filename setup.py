import os
import sys
from setuptools import setup

os.chdir(os.path.dirname(os.path.realpath(__file__)))
OS_WINDOWS = os.name == "nt"


def get_requirements():
    """
    To update the requirements for advent, edit the requirements.txt file.
    """
    with open("requirements.txt", "r") as f:
        req_lines = f.readlines()
    reqs = []
    for line in req_lines:
        # Avoid adding comments.
        line = line.split("#")[0].strip()
        if line:
            reqs.append(line)
    return reqs


def get_scripts():
    """
    Determine which executable scripts should be added. For Windows,
    this means creating a .bat file.
    """
    if OS_WINDOWS:
        batpath = os.path.join("bin", "windows", "mudforge.bat")
        scriptpath = os.path.join(sys.prefix, "Scripts", "advent_launcher.py")
        with open(batpath, "w") as batfile:
            batfile.write('@"%s" "%s" %%*' % (sys.executable, scriptpath))
        return [batpath, os.path.join("bin", "windows", "mudforge_launcher.py")]
    else:
        return [os.path.join("bin", "unix", "mudforge")]


from os import path

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

# setup the package
setup(
    name="mudforge",
    version="0.1.0",
    author="VolundMush",
    maintainer="VolundMush",
    url="https://github.com/volundmush/mudforge",
    description="",
    license="LGPL",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=["mudforge",],
    install_requires=get_requirements(),
    zip_safe=False,
    scripts=get_scripts(),
    classifiers=[
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.8",
        "Intended Audience :: Developers",
        "Topic :: Games/Entertainment :: Multi-User Dungeons (MUD)",
        "Topic :: Games/Entertainment :: Puzzle Games",
        "Topic :: Games/Entertainment :: Role-Playing",
        "Topic :: Games/Entertainment :: Simulation",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
    ],
    python_requires=">=3.8",
    project_urls={
        "Source": "https://github.com/volundmush/adventkai",
        "Issue tracker": "https://github.com/volundmush/adventkai/issues",
    },
)
