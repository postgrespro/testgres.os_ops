try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

install_requires = [
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
