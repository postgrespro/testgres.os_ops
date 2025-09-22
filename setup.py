try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

# Basic dependencies
install_requires = [
    "psutil",
    "six>=1.9.0",
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
