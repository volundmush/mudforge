import os
import sys
from setuptools import setup, find_packages

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


def package_data():
    """
    By default, the distribution tools ignore all non-python files.
    Make sure we get everything.
    """
    file_set = []
    for root, dirs, files in os.walk("mudforge"):
        for f in files:
            if ".git" in f.split(os.path.normpath(os.path.join(root, f))):
                # Prevent the repo from being added.
                continue
            file_name = os.path.relpath(os.path.join(root, f), "mudforge")
            file_set.append(file_name)
    return file_set


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
    packages=find_packages(),
    package_data={"": package_data()},
    install_requires=get_requirements(),
    zip_safe=False,
    scripts=get_scripts(),
    classifiers=[
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.10",
        "Intended Audience :: Developers",
        "Topic :: Games/Entertainment :: Multi-User Dungeons (MUD)",
        "Topic :: Games/Entertainment :: Puzzle Games",
        "Topic :: Games/Entertainment :: Role-Playing",
        "Topic :: Games/Entertainment :: Simulation",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
    ],
    python_requires=">=3.10",
    project_urls={
        "Source": "https://github.com/volundmush/mudforge",
        "Issue tracker": "https://github.com/volundmush/mudforge/issues",
    },
)
