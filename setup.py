try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

# Basic dependencies
install_requires = [
    "psutil",
    "testgres.common @ git+https://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@github.com/postgrespro/testgres.common.git",
]

setup(
    version="0.0.1",
    name="testgres.os_ops",
    packages=[
        "testgres.operations",
    ],
    package_dir={"testgres.operations": "src"},
    description='Testgres subsystem to work with OS',
    url='https://github.com/postgrespro/testgres.os_ops',
    long_description_content_type='text/markdown',
    license='PostgreSQL',
    author='Postgres Professional',
    author_email='testgres@postgrespro.ru',
    keywords=['testgres'],
    install_requires=install_requires,
)
