import os
import setuptools

with open("README.md", "r") as readme_file:
    long_description = readme_file.read()
with open("bitbot/VERSION", "r") as version_file:
    version = version_file.read().strip()

def list_modules(dirname):
    for (module_name, ext) in map(os.path.splitext, os.listdir(dirname)):
        if ext in ('', '.py') and not module_name.startswith('_'):
            yield module_name

package_dir = {
    # Install bitbot's modules as a separate 'bitbot_modules' package
    'bitbot_modules': 'modules',
}

for module_package in setuptools.find_packages('modules'):
    package_dir[f'bitbot_modules.{module_package}'] = \
        f'modules/{module_package}'

packages = setuptools.find_packages(exclude=['modules', 'modules.*'])

for package in package_dir:
    packages.append(package)

entry_points = {
    'bitbot.core_modules': [
        f'{module_name} = bitbot.core_modules.{module_name}:Module'
        for module_name in list_modules('bitbot/core_modules')
    ],
    'bitbot.extra_modules': [
        f'{module_name} = bitbot_modules.{module_name}:Module'
        for module_name in list_modules('modules')
    ],
}

setuptools.setup(
    name="bitbot",
    version=version,
    scripts=["bitbotd", "bitbotctl"],
    author="jesopo",
    author_email="bitbot@jesopo.uk",
    description="Modular event-driven IRC bot",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/jesopo/bitbot",

    packages=packages,
    include_package_data=True,
    package_dir=package_dir,
    package_data={
        '': ['VERSION'],
    },

    entry_points=entry_points,

    # We need to read hashflags of modules; and currently this is done by
    # opening the modules' files. So it doesn't work in a zip, because
    # module files are then not available.
    zip_safe=False,

    classifiers=[
        "Environment :: Console",
        "Environment :: No Input/Output (Daemon)",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
        "Operating System :: POSIX",
        "Topic :: Communications :: Chat :: Internet Relay Chat",
    ],
    platforms=["linux"],
    python_requires=">=3.6",
)
